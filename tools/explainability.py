import numpy as np

METHOD_NOTES = {
    "shap": "Giá trị SHAP: đóng góp của từng đặc trưng vào điểm của bệnh nhân so với trung bình dữ liệu huấn luyện.",
    "sensitivity": (
        "Phân tích độ nhạy: thay đổi xác suất dự đoán khi thay một đặc trưng bằng giá trị"
        " mặc định (trung vị huấn luyện), giữ nguyên các đặc trưng khác."
    ),
}

TRAIL_PASSAGE_FIELDS = (
    "evidence_id",
    "text",
    "source_title",
    "publisher",
    "year",
    "url",
    "relevance",
    "supports",
)


class FeatureExplainer:
    def __init__(self, risk_model):
        self.risk_model = risk_model
        self.method = "sensitivity"
        self._shap_explainer = None
        self._build_shap_explainer()

    def _build_shap_explainer(self):
        try:
            import shap

            if self.risk_model.training_frame is None:
                return
            if not hasattr(self.risk_model.model, "coef_"):
                return

            self._shap_explainer = shap.LinearExplainer(
                self.risk_model.model,
                self.risk_model.training_frame,
            )
            self.method = "shap"
        except Exception:
            self._shap_explainer = None
            self.method = "sensitivity"

    def explain(self, patient):
        row = self.risk_model.feature_frame(patient)
        values = self._shap_values(row)
        if values is None:
            values = self._sensitivity_values(row)

        defaulted = set(patient.get("defaulted_fields", []))
        impacts = []
        for feature, value, impact in zip(self.risk_model.feature_names, row.iloc[0], values):
            if np.isclose(impact, 0.0):
                direction = "no effect"
            else:
                direction = "raises risk" if impact > 0 else "lowers risk"
            impacts.append(
                {
                    "feature": feature,
                    "value": float(value),
                    "impact": float(impact),
                    "direction": direction,
                    "magnitude": abs(float(impact)),
                    # True when the caller gave no value, so `value` is the model's default.
                    "defaulted": feature in defaulted,
                }
            )

        impacts.sort(key=lambda item: item["magnitude"], reverse=True)
        return {
            "method": self.method,
            "method_note": METHOD_NOTES[self.method],
            "features": impacts,
            # Accepted measurements that no feature consumes directly (e.g. bp in mmHg).
            "inputs_not_in_model": self.risk_model.inputs_not_in_model(patient),
        }

    def _shap_values(self, row):
        if self._shap_explainer is None:
            return None

        try:
            raw_values = self._shap_explainer.shap_values(row)
            values = np.asarray(raw_values)

            if values.ndim == 3:
                values = values[:, :, -1]
            if values.ndim == 2:
                values = values[0]

            if values.shape[0] != len(self.risk_model.feature_names):
                return None

            return values
        except Exception:
            return None

    def _sensitivity_values(self, row):
        base_probability = self.risk_model.probability(row)
        values = []
        defaults = self.risk_model.default_values
        training_medians = self.risk_model.training_frame.median(numeric_only=True).to_dict()

        for feature in self.risk_model.feature_names:
            baseline_row = row.copy()
            baseline_value = defaults.get(
                feature, training_medians.get(feature, row.iloc[0][feature])
            )
            baseline_row.loc[:, feature] = baseline_value
            baseline_probability = self.risk_model.probability(baseline_row)
            values.append(base_probability - baseline_probability)

        return np.asarray(values)


def evidence_trail(feature_explanation, retrieved_context, limit=4):
    """For each top risk-raising driver, the retrieved passages the knowledge graph ties to it.

    Drivers the patient did not supply (model defaults) are skipped, and a driver with no
    linked passage keeps an empty `evidence` list instead of borrowing an unrelated one.
    """
    trail = []
    for item in feature_explanation.get("features", []):
        if item["impact"] <= 0 or item.get("defaulted"):
            continue
        trail.append(
            {
                "feature": item["feature"],
                "value": item.get("value"),
                "impact": item["impact"],
                "evidence": [
                    {key: passage.get(key) for key in TRAIL_PASSAGE_FIELDS}
                    for passage in retrieved_context
                    if item["feature"] in passage.get("factors", [])
                ],
            }
        )
        if len(trail) == limit:
            break
    return trail
