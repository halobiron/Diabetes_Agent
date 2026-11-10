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
    from agents.retriever import CHAT_MIN_RELEVANCE, RetrievalAgent
    from core.config import get_settings
    from tools.neo4j_kb import FileKnowledgeBase, load_kb_file
    from tools.semantic_embeddings import SemanticEmbeddingModel

    # Explicit injection makes this fixture independent of earlier imports / API fixtures.
    monkeypatch.setattr(main, "CHROMA_PATH", tmp_path / "chroma")
    # Offline acceptance tests inject their KB explicitly; production requires Neo4j.
    monkeypatch.setattr(
        main.RetrievalAgent,
        "from_settings",
        lambda settings, path: RetrievalAgent(
            FileKnowledgeBase(load_kb_file(settings.kb_path)),
            SemanticEmbeddingModel(),
            path,
            ask_min_relevance=CHAT_MIN_RELEVANCE,
        ),
    )
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
    with patch.object(
        api._get_agent().model, "assess", side_effect=RuntimeError("Model unavailable")
    ):
        response = client.post("/v1/predict", json={"age": 50, "bmi": 27, "bp": 120})
    assert response.status_code == 500
    assert "probability" not in response.text


def test_audit_log_records_request_id_versions_and_timing(tmp_path):
    import json

    logger = AuditLogger(tmp_path)
    result = {
        "risk": "High",
        "probability": 0.7,
        "evidence_status": "limited",
        "safety": {},
        "model": {"model_version": "mlp-x"},
        "degraded": [{"component": "retriever", "error": "boom"}],
        "trace": {
            "versions": {"risk_model": "mlp-x"},
            "total_ms": 12.5,
            "steps": [
                {
                    "component": "risk_model",
                    "agent": "diagnosis",
                    "status": "ok",
                    "ms": 3.0,
                    "version": "mlp-x",
                    "detail": "x",
                }
            ],
        },
    }
    logger.log_decision("req-1", {"age": 50}, result)
    entry = json.loads(logger.output_file.read_text(encoding="utf-8").splitlines()[0])

    assert entry["request_id"] == "req-1" and entry["model_version"] == "mlp-x"
    assert entry["total_ms"] == 12.5 and entry["degraded"] == ["retriever"]
    assert entry["steps"] == [
        {
            "component": "risk_model",
            "agent": "diagnosis",
            "status": "ok",
            "ms": 3.0,
            "version": "mlp-x",
        }
    ]
    assert entry["result"]["evidence_status"] == "limited"
