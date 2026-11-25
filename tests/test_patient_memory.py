"""Core patient-memory flow and API contract, without an external KB or LLM."""

import json
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from agents.explainer import ExplanationAgent
from agents.orchestrator import Orchestrator
from agents.recommender import RecommendationAgent
from memory.context import describe_memory
from memory.store import MemoryAgent
from tools.audit_logger import AuditLogger
from tools.safety import SafetyGuard


class Model:
    risk_bands = None
    decision_threshold = 0.3
    model_version = "test"
    artifact_metadata = {"selected_model": "fake"}

    def assess(self, data):
        return 0.2, dict(data)


@pytest.fixture
def agent(tmp_path):
    return Orchestrator(
        Model(),
        ExplanationAgent(),
        RecommendationAgent(),
        MemoryAgent(str(tmp_path / "chroma")),
        safety_guard=SafetyGuard(),
    )


def test_history_reaches_advice_and_does_not_change_model_output(agent):
    first = agent.run({"age": 50, "bmi": 30, "bp": 130})
    second = agent.run({"patient_id": first["patient_id"], "age": 50, "bmi": 28, "bp": 125})
    assert first["memory_context"]["status"] == "first_assessment"
    assert second["memory_context"]["assessment_count"] == 1
    assert second["memory_context"]["previous"]["id"] == first["assessment_id"]
    assert first["memory_saved"] and second["memory_saved"]
    assert describe_memory(second["memory_context"]) in second["explanation"]
    assert describe_memory(second["memory_context"]) in second["recommendation"]
    assert second["probability"] == first["probability"]
    assert len(agent.memory.get_all(patient_id=first["patient_id"])) == 2
    separate = agent.run({"age": 50, "bmi": 28, "bp": 125})
    assert separate["patient_id"] != first["patient_id"]
    assert separate["memory_context"]["status"] == "first_assessment"


def test_failed_memory_read_is_not_reported_as_first_assessment(agent, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(agent.memory, "recall", fail)
    monkeypatch.setattr(agent.memory, "store", fail)
    result = agent.run({"age": 50, "bmi": 30, "bp": 190})
    assert result["memory_context"]["status"] == "unavailable"
    assert result["memory_saved"] is False
    assert "Chưa đọc được lịch sử" in result["explanation"]
    assert {item["component"] for item in result["degraded"]} == {"memory_search", "memory_store"}
    assert result["safety"]["escalation"] == "urgent_clinician_review"


def test_api_filters_history_returns_summary_and_audits_assessment(agent, tmp_path, monkeypatch):
    import api.app as api
    from core.config import get_settings

    ready = Future()
    ready.set_result(agent)
    monkeypatch.setattr(api, "_agent_future", ready)
    monkeypatch.setenv("REQUIRE_API_TOKEN", "false")
    monkeypatch.setattr(api, "settings", get_settings())
    monkeypatch.setattr(api, "audit_logger", AuditLogger(tmp_path / "logs"))
    with TestClient(api.app) as client:
        profile = {"age": 50, "bmi": 30, "bp": 130}
        first = client.post("/v1/predict", json=profile).json()
        second = client.post(
            "/v1/predict", json={**profile, "patient_id": first["patient_id"], "bmi": 28}
        ).json()
        assert "BMI từ 30 thành 28" in describe_memory(second["memory_context"])
        assert len(client.get("/history?limit=25").json()["records"]) == 2
        client.post("/v1/predict", json={**profile, "patient_id": "another-patient"})
        for route in ("/history", "/v1/history"):
            records = client.get(
                route, params={"patient_id": first["patient_id"], "limit": 1}
            ).json()["records"]
            assert len(records) == 1 and records[0]["id"] == second["assessment_id"]
        for limit in (0, -1, 101):
            assert client.get("/v1/history", params={"limit": limit}).status_code == 422
        summary = client.post("/predict/summary", json=profile).json()
        assert summary["assessment_id"] and summary["patient_id"] and summary["memory_saved"]
        for invalid in ("bad id", "x" * 65, "../outside", 123):
            assert (
                client.post("/predict", json={**profile, "patient_id": invalid}).status_code == 422
            )
        normalized = client.post("/predict", json={**profile, "patient_id": " demo-a "}).json()
        assert normalized["patient_id"] == "demo-a"
    entries = [
        json.loads(line)
        for line in api.audit_logger.output_file.read_text(encoding="utf-8").splitlines()
    ]
    audited = next(entry for entry in entries if entry["assessment_id"] == second["assessment_id"])
    assert audited["patient_id"] == first["patient_id"] and audited["memory_saved"] is True


@pytest.mark.parametrize(
    "previous,current,expected",
    [
        ("v1", "v1", -0.2),
        ("v1", "v2", None),
        (None, "v1", None),
        (None, None, None),
        ("legacy-unversioned", "legacy-unversioned", None),
    ],
)
def test_probability_comparison_requires_same_known_model(agent, previous, current, expected):
    patient = {"patient_id": "a", "age": 50, "bmi": 30, "bp": 130}
    agent.memory.store(patient, 0.4, "Medium", model_version=previous)
    context = agent.memory.recall(patient, 0.2, "Low", current)
    assert context["prediction_comparison"]["probability_delta"] == expected
    assert context["prediction_comparison"]["comparable"] == (expected is not None)
    assert ("điểm phần trăm" in describe_memory(context)) == (expected is not None)


def test_history_contains_five_recent_records_with_full_count_and_survives_reopen(agent, tmp_path):
    patient = {"patient_id": "a", "age": 50, "bmi": 30, "bp": 130}
    for day in range(1, 8):
        record_id = agent.memory.store(patient, 0.2, "Low", model_version="v1")
        agent.memory.collection.update(
            ids=[record_id], metadatas=[{"timestamp": f"2025-01-{day:02}T00:00:00+00:00"}]
        )
    reopened = MemoryAgent(str(tmp_path / "chroma"))
    context = reopened.recall(patient, 0.2, "Low", "v1")
    assert context["assessment_count"] == 7 and len(context["recent_assessments"]) == 5
    assert context["previous"]["metadata"]["timestamp"].startswith("2025-01-07")
    assert all(record["metadata"]["patient_id"] == "a" for record in context["recent_assessments"])


def test_both_llm_prompts_receive_history_without_profile_identifier(agent):
    patient = {"patient_id": "private-profile", "age": 50, "bmi": 30, "bp": 130}
    agent.memory.store(patient, 0.4, "Medium", model_version="v1")
    current = {**patient, "bmi": 28}
    context = agent.memory.recall(current, 0.2, "Low", "v1")
    for text_agent in (agent.explainer, agent.recommender):
        create = Mock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )
        )
        text_agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        if isinstance(text_agent, ExplanationAgent):
            text_agent.explain(current, 0.2, memory_context=context)
        else:
            text_agent.recommend(current, "Low", memory_context=context)
        prompt = create.call_args.kwargs["messages"][0]["content"]
        assert "BMI từ 30 thành 28" in prompt and "private-profile" not in prompt
        assert "Never compare probabilities across model versions" in prompt


def test_short_ids_are_new_only_and_retry_existing_codes(agent, monkeypatch):
    import memory.store as store

    existing = "HS-ABCDEFGH23"
    agent.memory.store({"patient_id": existing, "age": 50, "bmi": 30, "bp": 130}, 0.2, "Low")
    candidates = iter([existing, "HS-ABCDEFGH24"])
    monkeypatch.setattr(store, "generate_patient_id", lambda: next(candidates))
    assert agent.memory.new_patient_id() == "HS-ABCDEFGH24"
    legacy = agent.run({"patient_id": "patient-legacy-long-code", "age": 50, "bmi": 30, "bp": 130})
    assert legacy["patient_id"] == "patient-legacy-long-code"


def test_profile_restores_latest_raw_inputs_with_false_zero_and_unknowns(agent):
    from memory.profiles import editable_inputs

    first = {"patient_id": "a", "age": 40, "bmi": 30, "bp": 130, "sex": "female"}
    agent.memory.store(first, 0.2, "Low", input_data=first)
    latest = {**first, "age": 41, "height_cm": 170, "weight_kg": 75, "bp": 125,
              "smoker": False, "phys_activity": True, "high_chol": None,
              "mental_health_days": 0, "physical_health_days": 3, "general_health": 2,
              "education": 4, "income": 5, "skipped_fields": ["high_chol"]}
    agent.memory.store(latest, 0.2, "Low", input_data=latest)
    profile = agent.memory.get_profile("a")
    assert profile["input"] == {**editable_inputs(latest), "patient_id": "a"}
    assert profile["input"]["smoker"] is False
    assert profile["input"]["mental_health_days"] == 0
    assert profile["input"]["high_chol"] is None
    assert len(agent.memory.get_all(patient_id="a")) == 2  # Loading never saves a new assessment.
    assert agent.memory.get_profile("unknown") is None


def test_legacy_prepared_profile_migrates_aliases_without_imputed_answers(agent):
    from models.risk_model import RiskModel

    model = RiskModel()
    model.feature_names = model.BRFSS_FEATURE_NAMES
    prepared = model.prepare_patient({"age": 56, "bmi": 29, "bp": 145, "smoker": False,
                                      "mental_health_days": 0, "general_health": 4, "sex": "male"})
    prepared["patient_id"] = "patient-old-id"
    agent.memory.store(prepared, 0.2, "Low")  # Existing storage has no raw input_json.
    restored = agent.memory.get_profile("patient-old-id")["input"]
    assert restored["height_cm"] is None and restored["weight_kg"] is None
    assert restored["bmi"] == 29 and restored["sex"] == "male"
    assert restored["general_health"] == 4 and restored["mental_health_days"] == 0
    assert restored["smoker"] is False and restored["phys_activity"] is None
    assert restored["income"] is None and restored["chol_check"] is None
    assert "gen_hlth" not in restored and "defaulted_fields" not in restored


def test_timeline_changes_group_habits_and_mark_direction(agent):
    base = {"patient_id": "timeline", "age": 50, "bmi": 30, "bp": 150, "smoker": True,
            "phys_activity": False, "fruits": True, "sex": "male"}
    second = {**base, "bmi": 27, "smoker": False, "phys_activity": True}
    third = {**second, "bp": 160, "fruits": False}
    for step, data in enumerate((base, second, third), start=1):
        record_id = agent.memory.store(data, 0.2, "Low", input_data=data, model_version="v1")
        agent.memory.collection.update(
            ids=[record_id], metadatas=[{"timestamp": f"2025-01-{step:02}T00:00:00+00:00"}]
        )
    memory = agent.memory.recall(third, 0.2, "Low", "v1")
    newest, middle, first = memory["recent_assessments"]
    assert first["changes"] is None  # nothing precedes the first assessment
    by_field = {item["field"]: item for item in middle["changes"]}
    assert set(by_field) == {"bmi", "smoker", "phys_activity"}  # unchanged answers never appear
    assert (by_field["smoker"]["group"], by_field["smoker"]["direction"]) == ("habit", "better")
    assert by_field["phys_activity"]["direction"] == "better"
    assert by_field["bmi"]["group"] == "body" and by_field["bmi"]["direction"] == "better"
    assert by_field["bmi"]["delta"] == -3 and by_field["smoker"]["delta"] is None
    latest = {item["field"]: item for item in newest["changes"]}
    assert (latest["fruits"]["group"], latest["fruits"]["direction"]) == ("habit", "worse")
    assert latest["bp"]["direction"] == "worse"
    assert memory["changes"] == []  # current answers equal the newest stored ones
    described = describe_memory(agent.memory.recall({**third, "smoker": True}, 0.2, "Low", "v1"))
    assert "Hút thuốc từ Không thành Có." in described


def test_profile_api_roundtrip_not_found_unavailable_and_auth(agent, monkeypatch, tmp_path):
    import api.app as api
    from core.config import get_settings

    ready = Future()
    ready.set_result(agent)
    monkeypatch.setattr(api, "_agent_future", ready)
    monkeypatch.setenv("REQUIRE_API_TOKEN", "false")
    monkeypatch.setattr(api, "settings", get_settings())
    monkeypatch.setattr(api, "audit_logger", AuditLogger(tmp_path / "logs"))
    patient = {"age": 46, "bmi": 28, "height_cm": 170, "weight_kg": 81,
               "bp": 132, "smoker": None, "sex": "female", "mental_health_days": 0}
    with TestClient(api.app) as client:
        result = client.post("/v1/predict", json=patient).json()
        patient_id = result["patient_id"]
        assert patient_id.startswith("HS-") and len(patient_id) == 13
        for route in ("/patients/", "/v1/patients/"):
            response = client.get(route + patient_id)
            assert response.status_code == 200
            profile = response.json()
            assert profile["assessment_id"] == result["assessment_id"]
            assert profile["input"]["smoker"] is None
            assert profile["input"]["sex"] == "female"
            updated = client.post("/v1/predict", json={**profile["input"], "bp": 120}).json()
            assert updated["patient_id"] == patient_id
            assert updated["memory_context"]["previous"]["metadata"]["bp"] in (120, 132)
            result = updated
        assert client.get("/v1/patients/missing").status_code == 404
        assert client.get("/v1/patients/bad%20id").status_code == 422
        monkeypatch.setattr(agent.memory, "get_profile", Mock(side_effect=RuntimeError("offline")))
        assert client.get("/v1/patients/any").status_code == 503
        monkeypatch.setenv("REQUIRE_API_TOKEN", "true")
        monkeypatch.setenv("API_TOKEN", "test-profile-token")
        monkeypatch.setattr(api, "settings", get_settings())
        assert client.get("/v1/patients/any").status_code == 401
