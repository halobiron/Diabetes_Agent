"""Acceptance scenarios across the HTTP API and real local agent components."""

from concurrent.futures import Future
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from scripts.demo_step12 import ROOT, run_api_scenarios
from tools.audit_logger import AuditLogger


@pytest.fixture
def integration_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("NEO4J_PASSWORD", "")
    monkeypatch.setenv("REQUIRE_API_TOKEN", "false")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("MODEL_ARTIFACT_PATH", str(ROOT / "artifacts/risk_model.joblib"))
    monkeypatch.setenv("SUPPORT_POLICY_PATH", str(ROOT / "artifacts/support_policy.json"))
    import api.app as api
    import main
    from core.config import get_settings

    # Explicit injection makes this fixture independent of earlier imports / API fixtures.
    monkeypatch.setattr(main, "CHROMA_PATH", tmp_path / "chroma")
    ready = Future()
    ready.set_result(main.build_agent())
    monkeypatch.setattr(api, "_agent_future", ready)
    monkeypatch.setattr(api, "settings", get_settings())
    monkeypatch.setattr(api, "audit_logger", AuditLogger(tmp_path / "logs"))
    with TestClient(api.app, raise_server_exceptions=False) as client:
        yield client, api


def test_real_artifact_api_acceptance_scenarios(integration_client):
    client, api = integration_client
    records = run_api_scenarios(client, api._get_agent(), api.audit_logger.output_file)
    assert len(records) == 16


def test_core_model_failure_does_not_return_a_prediction(integration_client):
    client, api = integration_client
    with patch.object(api._get_agent().model, "assess", side_effect=RuntimeError("Model unavailable")):
        response = client.post("/v1/predict", json={"age": 50, "bmi": 27, "bp": 120})
    assert response.status_code == 500
    assert "probability" not in response.text
