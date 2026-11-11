"""Measure end-to-end latency of the API on this machine (cold start and warm requests).

Runs the real FastAPI app in-process (the KB comes from Neo4j when NEO4J_PASSWORD is set), sends
each profile `--repeats` times to /v1/predict and each question to /v1/chat, and reports the
mean, median, p95 and max in milliseconds. The first request of each endpoint is reported
separately as the cold start and left out of the warm statistics.

Usage: python scripts/measure_latency.py [--repeats 10] [--output logs/latency.json]
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROFILES = {
    "nguy_co_thap": {"age": 30, "bmi": 22, "bp": 110},
    "nguy_co_cao": {"age": 55, "bmi": 33, "bp": 150},
    "huyet_ap_cao": {"age": 65, "bmi": 36, "bp": 160},
}
QUESTIONS = [
    "HbA1c bao nhiêu thì được chẩn đoán là đái tháo đường?",
    "Người tiền đái tháo đường nên ăn những gì?",
    "Thủ đô của nước Pháp là thành phố nào?",
]


def summary(values):
    values = sorted(values)
    p95 = values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))]
    return {
        "n": len(values),
        "mean_ms": round(statistics.mean(values), 1),
        "median_ms": round(statistics.median(values), 1),
        "p95_ms": round(p95, 1),
        "max_ms": round(values[-1], 1),
    }


def timed(call):
    started = time.perf_counter()
    response = call()
    return (time.perf_counter() - started) * 1000, response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "logs/latency.json")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ.update(
            {
                "OPENAI_API_KEY": "",
                "REQUIRE_API_TOKEN": "false",
                "CHROMA_PATH": str(Path(tmp) / "chroma"),
                "LOG_DIR": str(Path(tmp) / "logs"),
            }
        )
        from fastapi.testclient import TestClient

        from api.app import app

        predict_wall = {name: [] for name in PROFILES}
        predict_cold = {}
        component_ms = {}
        total_ms = []
        chat_wall = {question: [] for question in QUESTIONS}
        chat_cold = {}
        with TestClient(app) as client:
            for name, profile in PROFILES.items():
                for run in range(args.repeats + 1):
                    wall, response = timed(lambda: client.post("/v1/predict", json=profile))
                    assert response.status_code == 200, response.text
                    if run == 0 and not predict_cold:
                        predict_cold[name] = round(wall, 1)
                        continue
                    if run == 0:
                        continue  # only the very first request of the process is a cold start
                    predict_wall[name].append(wall)
                    trace = response.json()["trace"]
                    total_ms.append(trace["total_ms"])
                    for step in trace["steps"]:
                        component_ms.setdefault(step["component"], []).append(step["ms"])
            for question in QUESTIONS:
                for run in range(args.repeats + 1):
                    wall, response = timed(
                        lambda: client.post("/v1/chat", json={"question": question})
                    )
                    assert response.status_code == 200, response.text
                    if run == 0 and not chat_cold:
                        chat_cold[question] = round(wall, 1)
                        continue
                    if run == 0:
                        continue
                    chat_wall[question].append(wall)
            import api.app as api_module

            kb_source = api_module._get_agent().retriever.kb_source

    all_predict = [v for values in predict_wall.values() for v in values]
    all_chat = [v for values in chat_wall.values() for v in values]
    result = {
        "kb_source": kb_source,
        "repeats_per_input": args.repeats,
        "note": "In-process TestClient on one machine, CPU inference, no network; not a load test.",
        "predict_cold_start_ms": predict_cold,
        "predict_warm": summary(all_predict),
        "predict_warm_by_profile": {name: summary(v) for name, v in predict_wall.items()},
        "predict_pipeline_total_ms": summary(total_ms),
        "predict_component_ms": {
            name: summary(values) for name, values in sorted(component_ms.items())
        },
        "chat_cold_start_ms": chat_cold,
        "chat_warm": summary(all_chat),
        "chat_warm_by_question": {q: summary(v) for q, v in chat_wall.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
