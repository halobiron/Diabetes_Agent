"""Repeatable integration demo using real artifacts, RAG, rules, policy and memory.

Run after `npm run build` in web: python scripts/demo_step12.py --with-web
Fault injection is scoped to this process; no production demo endpoints are added.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

COMPLETE = {
    "age": 50,
    "height_cm": 170,
    "weight_kg": 78,
    "bp": 120,
    "glucose": 90,
    "high_chol": False,
    "chol_check": True,
    "smoker": False,
    "stroke": False,
    "heart_disease_or_attack": False,
    "phys_activity": True,
    "fruits": True,
    "veggies": True,
    "heavy_alcohol_consump": False,
    "any_healthcare": True,
    "no_doc_bc_cost": False,
    "general_health": 2,
    "mental_health_days": 0,
    "physical_health_days": 0,
    "diff_walk": False,
    "sex": "female",
    "education": 5,
    "income": 6,
}
MISSING = {"age": 50, "bmi": 27, "bp": 120, "glucose": None}
WARNING = {**COMPLETE, "bp": 190, "glucose": 320}


def record(name, response):
    body = response.json()
    return {"scenario": name, "status": response.status_code, "response": body}


def run_api_scenarios(client, agent, audit_file):
    """Assertions are the acceptance criteria; any failure stops the demo with exit 1."""
    records = []

    def predict(name, patient=COMPLETE):
        response = client.post("/v1/predict", json=patient)
        assert response.status_code == 200, response.text
        records.append(record(name, response))
        result = response.json()
        assert result["request_id"]
        assert 0 <= result["prediction"]["probability"] <= 1
        assert result["prediction"]["model_version"] != "legacy-unversioned"
        assert result["explanation"] and result["recommendation"]
        return result

    full = predict("complete_profile")
    assert full["safety"]["confidence_score"] == 1
    assert full["patient"]["defaulted_fields"] == []
    assert full["feature_explanation"]["method"] in {"shap", "sensitivity"}
    assert full["retrieved_context"] and full["degraded"] == []
    assert full["policy"] and full["policy"]["steps"]
    for context in full["retrieved_context"]:
        assert context["evidence_id"] and context["url"] and context["source_title"]

    sparse = predict("missing_optional_data", MISSING)
    assert sparse["patient"]["glucose_measured"] is False
    assert sparse["patient"]["defaulted_fields"]
    assert sparse["safety"]["confidence_score"] < full["safety"]["confidence_score"]
    assert "GLU-300" not in {r["code"] for r in sparse["safety"]["rules"]}

    warning = predict("measurement_alerts", WARNING)
    codes = {r["code"] for r in warning["safety"]["rules"]}
    assert {"GLU-300", "BP-180"} <= codes
    assert warning["safety"]["escalation"] == "urgent_clinician_review"
    assert warning["policy"]["next_step"] == "escalate_to_clinician"

    for name, contexts, expected in [
        ("no_evidence", [], "none"),
        ("limited_evidence", full["retrieved_context"][:1], "limited"),
    ]:
        with patch.object(agent.retriever, "retrieve", return_value=contexts):
            result = predict(name, WARNING)
        assert result["evidence_status"] == expected
        assert result["safety"]["escalation"] == "urgent_clinician_review"
        assert result["degraded"] == []  # no matching evidence is not a service failure
        if expected == "none":
            assert "Chưa truy xuất được bằng chứng hướng dẫn đủ phù hợp" in result["recommendation"]
        else:
            assert "Bằng chứng hỗ trợ còn hạn chế" in result["recommendation"]

    faults = [
        (agent.retriever, "retrieve", "retriever"),
        (agent.memory, "find_similar", "memory_search"),
        (agent.memory, "store", "memory_store"),
        (agent.feature_explainer, "explain", "feature_explainer"),
        (agent.explainer, "explain", "explainer"),
        (agent.recommender, "recommend", "recommender"),
        (agent.safety_guard, "assess", "safety_guard"),
        (agent.support_policy, "decide", "support_policy"),
    ]
    for target, method, component in faults:
        with patch.object(target, method, side_effect=ConnectionError("Demo service unavailable")):
            result = predict(f"failure_{component}", WARNING)
        assert component in {d["component"] for d in result["degraded"]}
        assert any("chưa đầy đủ" in text for text in result["safety"]["disclaimers"])
        if component == "safety_guard":
            assert result["safety"]["confidence_score"] == 0
            assert result["safety"]["escalation"] != "routine_followup"
        else:
            assert result["safety"]["escalation"] == "urgent_clinician_review"

    response = client.post("/v1/predict", json={"age": 50, "bp": 120})
    assert response.status_code == 422
    records.append(record("missing_required_data", response))

    repeated = predict("repeat_profile_memory")
    assert repeated["similar_cases"]
    assert all(c["metadata"]["outcome_confirmed"] is False for c in repeated["similar_cases"])
    response = client.get("/history?limit=100")
    assert response.status_code == 200 and response.json()["records"]
    records.append(record("history", response))

    entries = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
    ids = {entry["request_id"] for entry in entries}
    assert all(
        r["response"]["request_id"] in ids
        for r in records
        if r["status"] == 200 and "request_id" in r["response"]
    )
    return records


def wait_ready(process, url, log_path):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Service exited: {log_path.read_text(encoding='utf-8', errors='replace')}"
            )
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Service not ready: {url}; see {log_path}")


def run_web_scenarios(env, work_dir, api_port, web_port):
    """Real HTTP: Next.js production server -> FastAPI -> real agent components."""
    records = []
    api_url = f"http://127.0.0.1:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    with ExitStack() as stack:

        def start(command, cwd, name, service_env):
            log_path = work_dir / f"{name}.log"
            handle = stack.enter_context(log_path.open("w", encoding="utf-8"))
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=service_env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            def stop():
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)

            stack.callback(stop)
            return process, log_path

        backend, backend_log = start(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            ROOT,
            "backend",
            env,
        )
        wait_ready(backend, f"{api_url}/health", backend_log)
        frontend, frontend_log = start(
            [
                shutil.which("node") or "node",
                str(ROOT / "web/node_modules/next/dist/bin/next"),
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(web_port),
            ],
            ROOT / "web",
            "frontend",
            {**env, "API_BASE_URL": api_url},
        )
        wait_ready(frontend, web_url, frontend_log)
        with httpx.Client(base_url=web_url, timeout=60) as client:
            page = client.get("/")
            assert page.status_code == 200 and "<html" in page.text
            records.append({"scenario": "web_page", "status": page.status_code})
            response = client.get("/api/health")
            assert response.status_code == 200 and response.json()["version"] == "v1"
            records.append(record("web_health", response))
            for name, patient in [
                ("complete", COMPLETE),
                ("missing", MISSING),
                ("warning", WARNING),
            ]:
                response = client.post("/api/predict", json=patient)
                assert response.status_code == 200, response.text
                result = response.json()
                assert result["request_id"] and result["degraded"] == []
                assert result["prediction"]["model_version"] != "legacy-unversioned"
                if name == "missing":
                    assert result["patient"]["glucose_measured"] is False
                if name == "warning":
                    assert result["safety"]["escalation"] == "urgent_clinician_review"
                records.append(record(f"web_{name}", response))
            response = client.post("/api/predict", json={"age": 50, "bp": 120})
            assert response.status_code == 422
            records.append(record("web_validation", response))
            response = client.get("/api/history")
            assert response.status_code == 200 and len(response.json()["records"]) >= 3
            records.append(record("web_history", response))

            # Stop only the backend created here. Verify the frontend's actual network fallback.
            backend.terminate()
            backend.wait(timeout=10)
            for route in ("health", "history", "predict"):
                response = (
                    client.post("/api/predict", json=COMPLETE)
                    if route == "predict"
                    else client.get(f"/api/{route}")
                )
                assert response.status_code == 502 and response.json()["detail"]
                records.append(record(f"web_backend_down_{route}", response))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-web", action="store_true")
    parser.add_argument(
        "--require-neo4j",
        action="store_true",
        help="Verify Neo4j graph contents (application startup always requires Neo4j).",
    )
    parser.add_argument("--api-port", type=int, default=18000)
    parser.add_argument("--web-port", type=int, default=13000)
    parser.add_argument("--output", type=Path, default=ROOT / "logs/step12-demo.json")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="healthcare-step12-") as temp:
        work_dir = Path(temp)
        isolated = {
            "OPENAI_API_KEY": "",
            "API_TOKEN": "",
            "REQUIRE_API_TOKEN": "false",
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", ""),
            "CHROMA_PATH": str(work_dir / "chroma"),
            "LOG_DIR": str(work_dir / "audit"),
            "MODEL_ARTIFACT_PATH": str(ROOT / "artifacts/risk_model.joblib"),
            "SUPPORT_POLICY_PATH": str(ROOT / "artifacts/support_policy.json"),
            "ANONYMIZED_TELEMETRY": "False",
        }
        with patch.dict(os.environ, isolated):
            import api.app as api

            graph_checks = None
            if args.require_neo4j:
                from tools.neo4j_kb import KnowledgeGraph

                kb = api._get_agent().retriever.kb
                assert isinstance(kb, KnowledgeGraph), (
                    "Neo4j required; KB file fallback is not accepted"
                )
                evidence = kb.all_evidence()
                links = kb.support_for_risk_factors(["BMI", "HighBP", "glucose"])
                assert evidence and links, "Load the diabetes KB into Neo4j before this demo"
                assert all(item["url"] and item["evidence_id"] for item in links)
                graph_checks = {
                    "stats": kb.stats(),
                    "evidence_count": len(evidence),
                    "support_count": len(links),
                    "support_sample": links[:3],
                }

            with TestClient(api.app) as client:
                records = run_api_scenarios(client, api._get_agent(), api.audit_logger.output_file)
            if args.with_web:
                # Separate stores for the subprocess; no real patient history is touched.
                isolated["CHROMA_PATH"] = str(work_dir / "web-chroma")
                isolated["LOG_DIR"] = str(work_dir / "web-audit")
                records += run_web_scenarios(
                    {**os.environ, **isolated},
                    work_dir,
                    args.api_port,
                    args.web_port,
                )
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "python": sys.version,
                "model": api._get_agent().model.artifact_metadata,
                "kb_source": api._get_agent().retriever.kb_source,
                "graph_checks": graph_checks,
                "embedding_model": api._get_agent().retriever.embedding_model.name,
                "llm": "local fallback (no API key)",
                "web_included": args.with_web,
                "passed": len(records),
                "scenarios": records,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for item in records:
                print(f"PASS {item['scenario']} (HTTP {item['status']})")
            print(f"Saved {len(records)} checks to {args.output}")


if __name__ == "__main__":
    main()
