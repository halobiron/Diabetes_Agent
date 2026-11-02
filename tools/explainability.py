import numpy as np

METHOD_NOTES = {
    "shap": "SHAP values: each feature's contribution to this patient's score versus the training average.",
    "sensitivity": (
        "Sensitivity: change in predicted probability when one feature is replaced by its"
        " default (training median) and the others are kept."
    ),
}


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
            # Inputs the patient supplied that this model does not use (e.g. glucose, BRFSS model).
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
        base_probability = self.risk_model.model.predict_proba(row)[0][1]
        values = []
        defaults = self.risk_model.default_values
        training_medians = self.risk_model.training_frame.median(numeric_only=True).to_dict()

        for feature in self.risk_model.feature_names:
            baseline_row = row.copy()
            baseline_value = defaults.get(
                feature, training_medians.get(feature, row.iloc[0][feature])
            )
            baseline_row.loc[:, feature] = baseline_value
            baseline_probability = self.risk_model.model.predict_proba(baseline_row)[0][1]
            values.append(base_probability - baseline_probability)

        return np.asarray(values)
