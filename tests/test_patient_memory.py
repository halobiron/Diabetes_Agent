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
