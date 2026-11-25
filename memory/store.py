import json
from datetime import datetime, timezone
from uuid import uuid4

from memory.profiles import editable_inputs, generate_patient_id
from tools.chroma_client import create_persistent_client
from tools.local_embeddings import LocalEmbeddingModel
from tools.vietnamese import RISK_LABELS


class MemoryAgent:
    """Patient assessment history in ChromaDB, retrieved by metadata, not vector similarity."""

    def __init__(self, chroma_path):
        self.embedding_model = LocalEmbeddingModel()
        self.client = create_persistent_client(chroma_path)
        self.collection = self.client.get_or_create_collection("patient_memory")

    def store(self, patient_data, prob, risk, *, model_version=None, assessment_id=None, input_data=None):
        record_id = assessment_id or f"assessment-{uuid4()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        document = self._patient_summary(patient_data, prob, risk)
        metadata = self._metadata(patient_data, prob, risk, timestamp)
        metadata["assessment_id"] = record_id
        if input_data is not None:
            metadata["input_json"] = json.dumps(input_data)
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

    def new_patient_id(self):
        for _ in range(10):
            candidate = generate_patient_id()
            try:
                existing = self.collection.get(where={"patient_id": candidate}, limit=1, include=[])
            except Exception:
                # Memory failures are reported by recall/store; they must not prevent scoring.
                return candidate
            if not existing["ids"]:
                return candidate
        raise RuntimeError("Không tạo được mã hồ sơ mới.")

    def get_profile(self, patient_id):
        results = self.collection.get(where={"patient_id": patient_id}, include=["metadatas"])
        records = list(zip(results.get("ids", []), results.get("metadatas", [])))
        if not records:
            return None
        record_id, metadata = max(records, key=lambda row: row[1].get("timestamp", ""))
        patient = json.loads(metadata.get("input_json") or metadata["patient_json"])
        return {
            "patient_id": patient_id,
            "assessment_id": record_id,
            "saved_at": metadata["timestamp"],
            "input": {**editable_inputs(patient), "patient_id": patient_id},
        }

    # key, label, unit, value type, group, polarity (+1: yes/higher is favourable, -1: unfavourable, 0: neutral)
    CHANGE_FIELDS = (
        ("age", "Tuổi", "tuổi", None, "profile", 0),
        ("height_cm", "Chiều cao", "cm", None, "body", 0),
        ("weight_kg", "Cân nặng", "kg", None, "body", 0),
        ("bmi", "BMI", "kg/m²", None, "body", 0),
        ("bp", "Huyết áp tâm thu", "mmHg", None, "body", 0),
        ("high_chol", "Cholesterol cao", None, "yes_no", "medical", -1),
        ("chol_check", "Đã kiểm tra cholesterol", None, "yes_no", "medical", 1),
        ("smoker", "Hút thuốc", None, "yes_no", "habit", -1),
        ("stroke", "Tiền sử đột quỵ", None, "yes_no", "medical", -1),
        ("heart_disease_or_attack", "Tiền sử bệnh tim", None, "yes_no", "medical", -1),
        ("phys_activity", "Vận động thể chất", None, "yes_no", "habit", 1),
        ("fruits", "Ăn trái cây hằng ngày", None, "yes_no", "habit", 1),
        ("veggies", "Ăn rau hằng ngày", None, "yes_no", "habit", 1),
        ("heavy_alcohol_consump", "Uống nhiều rượu bia", None, "yes_no", "habit", -1),
        ("any_healthcare", "Tiếp cận dịch vụ y tế", None, "yes_no", "medical", 1),
        ("no_doc_bc_cost", "Rào cản chi phí khám", None, "yes_no", "medical", -1),
        ("diff_walk", "Khó khăn khi đi lại", None, "yes_no", "medical", -1),
        ("sex", "Giới tính", None, "sex", "profile", 0),
        ("general_health", "Sức khỏe tổng quát", None, "general_health", "medical", 0),
        ("mental_health_days", "Ngày sức khỏe tinh thần kém", "ngày", None, "medical", 0),
        ("physical_health_days", "Ngày sức khỏe thể chất kém", "ngày", None, "medical", 0),
        ("education", "Trình độ học vấn", None, None, "profile", 0),
        ("income", "Mức thu nhập", None, None, "profile", 0),
    )
    MEASURES = ("age", "height_cm", "weight_kg", "bmi", "bp")

    @staticmethod
    def _direction(key, value_type, polarity, old, new):
        """Whether a change moves a risk factor the favourable way. Not a diagnosis."""
        if value_type == "yes_no":
            if not polarity or bool(old) == bool(new):
                return "neutral"
            return "better" if bool(new) == (polarity > 0) else "worse"
        # Numeric measures where "closer to the reference range / fewer days" is favourable.
        distance = {
            "bmi": lambda x: max(18.5 - x, 0, x - 24.9),
            "bp": lambda x: max(x - 120, 0),
            "general_health": lambda x: x,
            "mental_health_days": lambda x: x,
            "physical_health_days": lambda x: x,
        }.get(key)
        if distance is None:
            return "neutral"
        try:
            before, after = distance(float(old)), distance(float(new))
        except (TypeError, ValueError):
            return "neutral"
        return "neutral" if before == after else "better" if after < before else "worse"

    def _inputs(self, metadata):
        """What the patient actually answered; model defaults are not facts and stay unknown."""
        inputs = json.loads(metadata.get("input_json") or metadata.get("patient_json") or "{}")
        inputs = self._answers(inputs)
        for key in self.MEASURES:  # Older records always carry these as metadata.
            if inputs.get(key) is None and metadata.get(key) is not None:
                inputs[key] = metadata[key]
        return inputs

    @staticmethod
    def _answers(inputs):
        return editable_inputs(inputs) if "defaulted_fields" in inputs else dict(inputs)

    def _diff(self, previous_inputs, current_inputs):
        """Only answers that changed, each with its group and whether it moved the favourable way."""
        changes = []
        for key, label, unit, value_type, group, polarity in self.CHANGE_FIELDS:
            old = previous_inputs.get(key)
            new = current_inputs.get(key)
            if old is None or new is None:
                continue
            # Browser/profile payloads may encode the same number as either a JSON
            # number or numeric text. Compare those as numbers to avoid false changes.
            try:
                old_number, new_number = float(old), float(new)
                if old_number == new_number:
                    continue
            except (TypeError, ValueError):
                old_number = new_number = None
                if old == new:
                    continue
            direction = self._direction(key, value_type, polarity, old, new)
            if value_type == "yes_no":
                old, new = ("Có" if old else "Không"), ("Có" if new else "Không")
            elif value_type == "sex":
                old = "Nam" if old in (1, "1", "male", "M", "m") else "Nữ"
                new = "Nam" if new in (1, "1", "male", "M", "m") else "Nữ"
            elif value_type == "general_health":
                labels = {1: "Rất tốt", 2: "Tốt", 3: "Khá", 4: "Trung bình", 5: "Kém"}
                old, new = labels.get(int(old), old), labels.get(int(new), new)
            elif old_number is not None:
                # 30.0 -> 30: whole numbers read better and match integer inputs.
                old, new = (int(x) if x.is_integer() else round(x, 2) for x in (old_number, new_number))
            numeric = isinstance(old, (int, float)) and isinstance(new, (int, float))
            changes.append({
                "field": key, "label": label, "previous": old, "current": new, "unit": unit,
                "delta": round(new - old, 3) if numeric else None,
                "group": group, "direction": direction,
            })
        return changes

    def _records(self, patient_id=None, with_inputs=False):
        options = {"include": ["metadatas"]}
        if patient_id is not None:
            options["where"] = {"patient_id": patient_id}
        results = self.collection.get(**options)
        records = []
        for record_id, metadata in zip(results.get("ids", []), results.get("metadatas", [])):
            record = {
                "id": record_id,
                "summary": self._patient_summary(
                    metadata, metadata.get("probability"), metadata.get("risk")
                ),
                "metadata": self._public_metadata(metadata),
            }
            if with_inputs:
                record["_inputs"] = self._inputs(metadata)
            records.append(record)
        records.sort(key=lambda item: item["metadata"].get("timestamp", ""), reverse=True)
        return records

    def _with_changes(self, records, count):
        """Newest-first records, each annotated with what changed since the one before it."""
        annotated = []
        for index, record in enumerate(records[:count]):
            older = records[index + 1] if index + 1 < len(records) else None
            annotated.append({
                **{key: value for key, value in record.items() if key != "_inputs"},
                # None marks the very first assessment: there is nothing to compare with.
                "changes": self._diff(older["_inputs"], record["_inputs"]) if older else None,
            })
        return annotated

    def recall(self, patient_data, prob, risk, model_version):
        """Recall only this patient's history before saving the current assessment."""
        full = self._records(patient_data["patient_id"], with_inputs=True)
        records = self._with_changes(full, 5)
        context = {
            "patient_id": patient_data["patient_id"],
            "status": "available" if full else "first_assessment",
            "assessment_count": len(full),
            "previous": records[0] if records else None,
            "recent_assessments": records,
            "changes": self._diff(full[0]["_inputs"], self._answers(patient_data)) if full else [],
            "prediction_comparison": None,
        }
        if not full:
            return context
        previous = full[0]["metadata"]
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
