import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "decisions.jsonl"

    def log_decision(self, request_id, patient, result):
        trace = result.get("trace") or {}
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "patient": {
                "age": patient.get("age"),
                "bmi": patient.get("bmi"),
                "bp": patient.get("bp"),
            },
            "result": {
                "risk": result.get("risk"),
                "probability": result.get("probability"),
                "confidence": result.get("safety", {}).get("confidence_label"),
                "escalation": result.get("safety", {}).get("escalation"),
                "alerts": result.get("safety", {}).get("alerts", []),
                "evidence_status": result.get("evidence_status"),
            },
            "model_version": (result.get("model") or {}).get("model_version"),
            "versions": trace.get("versions", {}),
            "total_ms": trace.get("total_ms"),
            "steps": [
                {k: step.get(k) for k in ("component", "agent", "status", "ms", "version")}
                for step in trace.get("steps", [])
            ],
            "degraded": [item.get("component") for item in result.get("degraded", [])],
        }
        with self.output_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
