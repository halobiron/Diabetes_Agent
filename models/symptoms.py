"""Strict symptom-model inputs. This task is separate from lifestyle-only BRFSS."""

from pathlib import Path

import joblib
import pandas as pd

from models.risk_model import RiskModel

SYMPTOM_FIELDS = {
    "polyuria": "Đi tiểu nhiều",
    "polydipsia": "Khát nước nhiều",
    "sudden_weight_loss": "Sụt cân đột ngột",
    "weakness": "Mệt hoặc yếu sức",
    "polyphagia": "Ăn nhiều hoặc hay đói",
    "genital_thrush": "Nấm sinh dục",
    "visual_blurring": "Nhìn mờ",
    "itching": "Ngứa",
    "irritability": "Dễ cáu gắt",
    "delayed_healing": "Vết thương lâu lành",
    "partial_paresis": "Yếu hoặc liệt một phần cơ thể",
    "muscle_stiffness": "Cứng cơ",
    "alopecia": "Rụng tóc",
    "obesity": "Béo phì (theo thông tin bạn biết)",
}
SYMPTOM_FEATURES = ["age", "Sex", *SYMPTOM_FIELDS]
SYMPTOM_ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts/symptom_model.joblib"
SOURCE_URL = "https://archive.ics.uci.edu/dataset/529/early+stage+diabetes+risk+"


def load_symptom_data(path):
    frame = pd.read_csv(path)
    frame.columns = [c.strip().lower().replace(" ", "_") for c in frame.columns]
    frame = frame.rename(columns={"gender": "Sex", "age": "age"})
    if frame.isna().any().any():
        raise ValueError(
            "Symptom data has missing values; do not silently impute labels or inputs."
        )
    for name in SYMPTOM_FIELDS:
        frame[name] = frame[name].map({"Yes": 1, "No": 0})
    frame["Sex"] = frame["Sex"].map({"Male": 1, "Female": 0})
    frame["target"] = frame["class"].map({"Positive": 1, "Negative": 0})
    if frame[[*SYMPTOM_FEATURES, "target"]].isna().any().any():
        raise ValueError("Unrecognized symptom categories or labels.")
    grouped = frame.groupby(SYMPTOM_FEATURES)["target"].nunique()
    if (grouped > 1).any():
        raise ValueError("Conflicting identical profiles need explicit group splitting.")
    raw_count = len(frame)
    frame = frame.drop_duplicates(subset=SYMPTOM_FEATURES).reset_index(drop=True)
    return frame[SYMPTOM_FEATURES], frame["target"], raw_count


class SymptomRiskModel(RiskModel):
    """Requires every symptom explicitly; unknown never means No."""

    def load_artifact(self, path=SYMPTOM_ARTIFACT):
        artifact = joblib.load(path)
        if artifact["feature_names"] != SYMPTOM_FEATURES:
            raise ValueError("Unexpected symptom feature schema.")
        metadata = artifact["metadata"]
        if not metadata.get("acceptance", {}).get("passed"):
            raise ValueError("Symptom model has not passed its declared acceptance gate.")
        self.model = artifact["model"]
        self.feature_names = list(SYMPTOM_FEATURES)
        self.default_values = artifact["default_values"]
        self.training_frame = artifact["training_frame"].copy()
        self.artifact_metadata = metadata
        self.is_trained = True
        return self

    def prepare_patient(self, patient_data):
        raw = dict(patient_data)
        symptoms = raw.get("symptoms") or {}
        if set(symptoms) != set(SYMPTOM_FIELDS) or any(
            not isinstance(value, bool) for value in symptoms.values()
        ):
            raise ValueError(
                "Cần trả lời Có/Không cho đủ 14 mục triệu chứng; Chưa rõ không phải Không."
            )
        if raw.get("sex") not in ("male", "female", "M", "F", "m", "f", "0", "1", 0, 1):
            raise ValueError("Cần cung cấp giới tính để dùng mô hình triệu chứng.")
        if not 16 <= raw.get("age", -1) <= 90:
            raise ValueError("Mô hình triệu chứng chỉ được khảo sát với tuổi 16–90.")
        patient = super().prepare_patient(raw)
        # Unused lifestyle inputs must not become fabricated patient facts.
        unanswered = []
        for feature, key in self.FEATURE_KEYS.items():
            aliases = self.OPTIONAL_FIELD_KEYS.get(feature, (key, feature))
            if self._get(raw, *aliases) is None:
                patient.pop(key, None)
                unanswered.append(feature)
        patient.update({key: int(value) for key, value in symptoms.items()})
        patient["symptoms"] = dict(symptoms)
        patient["screening_mode"] = "symptoms"
        patient["unanswered_fields"] = unanswered
        patient["defaulted_fields"] = []
        patient["optional_field_count"] = 0
        return patient
