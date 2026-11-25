import json
from datetime import datetime, timezone
from uuid import uuid4

from tools.chroma_client import create_persistent_client
from tools.local_embeddings import LocalEmbeddingModel
from tools.vietnamese import RISK_LABELS


class MemoryAgent:
    """Patient assessment history in ChromaDB, retrieved by metadata, not vector similarity."""

    def __init__(self, chroma_path):
        self.embedding_model = LocalEmbeddingModel()
        self.client = create_persistent_client(chroma_path)
        self.collection = self.client.get_or_create_collection("patient_memory")

    def store(self, patient_data, prob, risk, *, model_version=None, assessment_id=None):
        record_id = assessment_id or f"assessment-{uuid4()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        document = self._patient_summary(patient_data, prob, risk)
        metadata = self._metadata(patient_data, prob, risk, timestamp)
        metadata["assessment_id"] = record_id
        if model_version:
            metadata["model_version"] = model_version
        if patient_data.get("patient_id"):
            metadata["patient_id"] = patient_data["patient_id"]
        self.collection.add(
            ids=[record_id],
            documents=[document],
            metadatas=[metadata],
            # Preserve the existing collection format; history uses metadata filtering.
            embeddings=[self.embedding_model.embed_text(document)],
        )
        return record_id

    def get_all(self, limit=25, patient_id=None):
        return self._records(patient_id)[: max(0, limit)]

    def _records(self, patient_id=None):
        options = {"include": ["metadatas"]}
        if patient_id is not None:
            options["where"] = {"patient_id": patient_id}
        results = self.collection.get(**options)
        records = [
            {
                "id": record_id,
                "summary": self._patient_summary(
                    metadata, metadata.get("probability"), metadata.get("risk")
                ),
                "metadata": self._public_metadata(metadata),
            }
            for record_id, metadata in zip(results.get("ids", []), results.get("metadatas", []))
        ]
        records.sort(key=lambda item: item["metadata"].get("timestamp", ""), reverse=True)
        return records

    def recall(self, patient_data, prob, risk, model_version):
        """Recall only this patient's history before saving the current assessment."""
        records = self._records(patient_data["patient_id"])
        context = {
            "patient_id": patient_data["patient_id"],
            "status": "available" if records else "first_assessment",
            "assessment_count": len(records),
            "previous": records[0] if records else None,
            "recent_assessments": records[:5],
            "changes": [],
            "prediction_comparison": None,
        }
        if not records:
            return context
        previous = records[0]["metadata"]
        for field, unit in (
            ("age", "tuổi"),
            ("bmi", "kg/m²"),
            ("bp", "mmHg"),
            ("height_cm", "cm"),
            ("weight_kg", "kg"),
        ):
            before, current = previous.get(field), patient_data.get(field)
            if before is not None and current is not None:
                context["changes"].append(
                    {
                        "field": field,
                        "previous": before,
                        "current": current,
                        "delta": round(float(current) - float(before), 3),
                        "unit": unit,
                    }
                )
        previous_version = previous.get("model_version")
        comparable = bool(
            model_version
            and previous_version
            and model_version == previous_version
            and model_version != "legacy-unversioned"
        )
        context["prediction_comparison"] = {
            "comparable": comparable,
            "previous_model_version": previous_version,
            "current_model_version": model_version,
            "previous_probability": previous.get("probability"),
            "current_probability": prob,
            "previous_risk": previous.get("risk"),
            "current_risk": risk,
            "probability_delta": round(prob - previous["probability"], 6)
            if comparable and previous.get("probability") is not None
            else None,
            "note": (
                "Cùng phiên bản mô hình; chênh lệch dự đoán có thể do số đo hoặc thông tin đầu vào thay đổi, "
                "không xác nhận bệnh tiến triển hay cải thiện."
                if comparable
                else "Khác phiên bản mô hình hoặc thiếu phiên bản; không so sánh chênh lệch xác suất."
            ),
        }
        return context

    def _patient_summary(self, patient_data, prob, risk):
        probability = "chưa rõ" if prob is None else f"{prob:.3f}"
        risk_text = RISK_LABELS.get(risk, "chưa rõ")
        return (
            f"Tuổi {patient_data.get('age')}, BMI {patient_data.get('bmi')}, "
            f"huyết áp {patient_data.get('bp')}, "
            f"nguy cơ {risk_text}, xác suất {probability}"
        )

    def _metadata(self, patient_data, prob, risk, timestamp):
        metadata = {
            "timestamp": timestamp,
            # Stored cases are model predictions; no clinical outcome is ever recorded.
            "outcome_confirmed": False,
            "risk": risk,
            "probability": float(prob),
            "age": int(patient_data.get("age")),
            "bmi": float(patient_data.get("bmi")),
            "bp": int(patient_data.get("bp")),
            "patient_json": json.dumps(patient_data),
        }

        if patient_data.get("height_cm") is not None:
            metadata["height_cm"] = float(patient_data["height_cm"])
        if patient_data.get("weight_kg") is not None:
            metadata["weight_kg"] = float(patient_data["weight_kg"])

        return metadata

    @staticmethod
    def _public_metadata(metadata):
        fields = (
            "patient_id",
            "assessment_id",
            "model_version",
            "timestamp",
            "outcome_confirmed",
            "risk",
            "probability",
            "age",
            "bmi",
            "bp",
            "height_cm",
            "weight_kg",
        )
        return {key: metadata[key] for key in fields if key in metadata}
