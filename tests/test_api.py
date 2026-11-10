from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client(tmp_path_factory, knowledge_graph):
    test_dir = tmp_path_factory.mktemp("api")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("OPENAI_API_KEY", "")
        patch.setenv("REQUIRE_API_TOKEN", "false")
        patch.setenv("CHROMA_PATH", str(test_dir / "chroma"))
        patch.setenv("LOG_DIR", str(test_dir / "logs"))
        patch.setenv("MODEL_ARTIFACT_PATH", str(PROJECT_ROOT / "artifacts/risk_model.joblib"))
        import main
        from agents.retriever import CHAT_MIN_RELEVANCE, RetrievalAgent
        from tools.semantic_embeddings import SemanticEmbeddingModel

        patch.setattr(
            main.RetrievalAgent,
            "from_settings",
            lambda settings, path: RetrievalAgent(
                knowledge_graph,
                SemanticEmbeddingModel(),
                path,
                ask_min_relevance=CHAT_MIN_RELEVANCE,
            ),
        )
        from api.app import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_followup_answer_updates_guidance_without_changing_mlp_probability(client):
    profile = {"age": 45, "bmi": 27, "bp": 120, "glucose": None}
    before = client.post("/v1/predict", json=profile).json()
    assert before["followup"]["kind"] == "glucose"
    assert before["measurement_scales"][2]["value"] is None

    after = client.post(
        "/v1/predict", json={**profile, "glucose": 126, "glucose_context": "fasting"}
    ).json()
    assert after["patient"]["glucose_context"] == "fasting"
    assert after["probability"] == before["probability"]
    assert after["measurement_scales"][2]["status"] == "Từ 126: cần xác nhận"
    assert after["followup"] is None  # no unknown input could move this low estimate by 2 points
    # Glucose changes clinical guidance, but is not a deduction in the input-quality score.
    assert after["safety"]["confidence_score"] == before["safety"]["confidence_score"]
    assert after["safety"]["confidence_reasons"] == before["safety"]["confidence_reasons"]


def test_unavailable_answer_suppresses_question_and_policy_reask(client):
    response = client.post(
        "/v1/predict", json={"age": 45, "bmi": 27, "bp": 120, "glucose_unavailable": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["followup"] is None
    assert body["patient"]["glucose_unavailable"] is True
    assert all(step["action"] != "request_glucose" for step in body["policy"]["steps"])


def test_glucose_context_validation_and_urgent_question_suppression(client):
    base = {"age": 45, "bmi": 27, "bp": 190}
    assert (
        client.post("/v1/predict", json={**base, "glucose_context": "invalid"}).status_code == 422
    )
    body = client.post("/v1/predict", json=base).json()
    assert body["followup"] is None
    assert body["safety"]["escalation"] == "urgent_clinician_review"


def test_v1_health_endpoint(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "v1"


def test_predict_summary_contains_safety(client):
    payload = {
        "age": 58,
        "height_cm": 168,
        "weight_kg": 92,
        "bp": 172,
        "glucose": 245,
    }
    response = client.post("/predict/summary", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["risk"] in {"Low", "Medium", "High"}
    assert 0 <= body["probability"] <= 1
    assert body["confidence"] in {"Low", "Medium", "High"}
    assert body["escalation"] in {
        "routine_followup",
        "prompt_clinician_followup",
        "urgent_clinician_review",
    }


def test_predict_summary_v1_contains_request_id(client):
    payload = {
        "age": 42,
        "height_cm": 172,
        "weight_kg": 79,
        "bp": 130,
        "glucose": 110,
    }
    response = client.post("/v1/predict/summary", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["request_id"], str)
    assert len(body["request_id"]) > 8


@pytest.mark.parametrize(
    "endpoint, measurements, expected_bmi",
    [
        ("/predict", {"bmi": 30, "height_cm": None, "weight_kg": None}, 30),
        ("/v1/predict", {"height_cm": 170, "weight_kg": 80}, 27.7),
    ],
)
def test_predict_accepts_body_measurements(client, endpoint, measurements, expected_bmi):
    response = client.post(endpoint, json={"age": 52, "bp": 140, **measurements})

    assert response.status_code == 200
    assert response.json()["patient"]["bmi"] == expected_bmi


@pytest.mark.parametrize("measurements", [{}, {"height_cm": 170}, {"weight_kg": 80}])
def test_predict_requires_bmi_or_height_and_weight(client, measurements):
    response = client.post("/v1/predict", json={"age": 52, "bp": 140, **measurements})

    assert response.status_code == 422
    assert any(
        "Cần cung cấp BMI hoặc cả chiều cao và cân nặng." in error["msg"]
        for error in response.json()["detail"]
    )


def test_predict_rejects_zero_bmi(client):
    response = client.post("/v1/predict", json={"age": 52, "bp": 140, "bmi": 0})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "bmi"


def test_predict_returns_probability_label_and_model_version(client):
    response = client.post(
        "/v1/predict",
        json={"age": 52, "bp": 140, "height_cm": 170, "weight_kg": 80},
    )
    assert response.status_code == 200
    prediction = response.json()["prediction"]
    assert 0 <= prediction["probability"] <= 1
    assert prediction["label"] in {0, 1, None}  # None: legacy model without a threshold
    assert prediction["risk_level"] in {"Low", "Medium", "High"}
    assert prediction["model_version"]


def test_what_if_and_evidence_trail_are_returned_with_citations(client):
    body = client.post(
        "/v1/predict",
        json={
            "age": 45,
            "height_cm": 170,
            "weight_kg": 95,
            "bp": 145,
            "glucose": 90,
            "smoker": True,
        },
    ).json()

    assert body["what_if"]["scenarios"]
    assert all(entry["evidence"] for entry in body["what_if"]["scenarios"])
    assert body["evidence_trail"] and all("evidence" in item for item in body["evidence_trail"])


def test_declined_question_is_not_asked_again_and_unknown_fields_are_rejected(client):
    profile = {"age": 55, "bmi": 32, "bp": 145, "glucose": 90, "glucose_context": "fasting"}
    first = client.post("/v1/predict", json=profile).json()["followup"]
    assert first["kind"] == "risk_factor"

    again = client.post("/v1/predict", json={**profile, "skipped_fields": [first["field"]]}).json()
    assert again["followup"] is None or again["followup"]["field"] != first["field"]
    assert (
        client.post("/v1/predict", json={**profile, "skipped_fields": ["age"]}).status_code == 422
    )


def test_grouped_followup_accepts_multiple_answers_and_skips_remaining_in_one_request(client):
    from tools.what_if import ASKABLE_FIELDS

    profile = {"age": 45, "bmi": 28.5, "bp": 130, "glucose_unavailable": True}
    before = client.post("/v1/predict", json=profile).json()
    skipped = [field for field in ASKABLE_FIELDS if field not in {"high_chol", "smoker"}]
    response = client.post(
        "/v1/predict",
        json={**profile, "high_chol": True, "smoker": False, "skipped_fields": skipped},
    )
    assert response.status_code == 200
    after = response.json()
    assert after["patient"]["high_chol"] == 1
    assert after["patient"]["smoker"] == 0
    assert "HighChol" not in after["safety"]["defaulted_fields"]
    assert "Smoker" not in after["safety"]["defaulted_fields"]
    assert after["safety"]["confidence_score"] > before["safety"]["confidence_score"]
    assert after["followup"] is None


def test_chat_returns_cited_answer_and_trace(client):
    response = client.post(
        "/v1/chat", json={"question": "Triệu chứng sớm của đái tháo đường là gì?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] and body["trace"]["passages_in_index"] > 0


def test_chat_rejects_empty_question(client):
    assert client.post("/v1/chat", json={"question": ""}).status_code == 422


def test_kb_overview_and_entity_detail(client):
    body = client.get("/v1/kb").json()
    assert body["source"] == "neo4j"
    assert body["entities"] and body["relations"] and body["evidence_count"] > 0

    entity_id = body["relations"][0]["from"]
    detail = client.get(f"/v1/kb/entities/{entity_id}")
    assert detail.status_code == 200
    assert detail.json()["relations"]
