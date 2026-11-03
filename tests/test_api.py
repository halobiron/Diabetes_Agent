from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("api")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("OPENAI_API_KEY", "")
        patch.setenv("REQUIRE_API_TOKEN", "false")
        patch.setenv("CHROMA_PATH", str(test_dir / "chroma"))
        patch.setenv("LOG_DIR", str(test_dir / "logs"))
        patch.setenv("MODEL_ARTIFACT_PATH", str(PROJECT_ROOT / "artifacts/risk_model.joblib"))
        from api.app import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
        "Provide bmi or both height_cm and weight_kg." in error["msg"]
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
