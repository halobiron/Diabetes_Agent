import time

from tools.risk_classifier import classify_risk
from tools.vietnamese import METHOD_LABELS, RISK_LABELS


class DiagnosisAgent:
    """Runs the deep-learning risk model and explains which inputs drove its answer.

    The model is required: if it fails the error propagates and no prediction is returned.
    Explaining the features is optional and degrades to an empty explanation.
    """

    NO_EXPLANATION = {"method": "none", "features": []}

    def __init__(self, model, feature_explainer=None):
        self.model = model
        self.feature_explainer = feature_explainer

    def diagnose(self, patient_data, log):
        started = time.perf_counter()
        prob, patient = self.model.assess(patient_data)
        risk = classify_risk(prob, self.model.risk_bands)
        log.record(
            "risk_model", started, "ok", f"xác suất {prob:.1%}, nguy cơ {RISK_LABELS.get(risk, risk)}"
        )
        threshold = self.model.decision_threshold
        prediction = {
            "probability": prob,
            # 1 = flagged by the binary threshold chosen on validation; None when unknown.
            "label": int(prob >= threshold) if threshold is not None else None,
            "threshold": threshold,
            "risk_level": risk,
            "model": self.model.artifact_metadata.get("selected_model"),
            "model_version": self.model.model_version,
        }
        feature_explanation = log.guard(
            "feature_explainer",
            lambda: (
                self.feature_explainer.explain(patient)
                if self.feature_explainer is not None
                else self.NO_EXPLANATION
            ),
            self.NO_EXPLANATION,
            detail=lambda value: (
                f"{METHOD_LABELS.get(value['method'], value['method'])}, "
                f"{len(value['features'])} đặc trưng"
            ),
            on_failure="dùng ngưỡng đơn giản thay giải thích của mô hình",
        )
        return {
            "probability": prob,
            "patient": patient,
            "risk": risk,
            "prediction": prediction,
            "feature_explanation": feature_explanation,
        }
