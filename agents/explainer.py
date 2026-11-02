import os

from openai import OpenAI


class ExplanationAgent:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def explain(
        self,
        patient_data,
        prob,
        feature_explanation=None,
        similar_cases=None,
        safety=None,
        evidence_status=None,
    ):
        if self.client is None:
            return self._fallback_explanation(
                patient_data, prob, feature_explanation, similar_cases, safety, evidence_status
            )

        prompt = f"""
        Patient data: {patient_data}
        Risk probability: {prob}
        Feature explanation: {feature_explanation}
        Similar prior cases (earlier model predictions, not confirmed outcomes): {similar_cases}
        Safety assessment (rules applied to the measurements): {safety}
        Guideline evidence status: {evidence_status}

        Explain in simple terms why this patient has this risk. If the safety assessment
        raised the risk or an escalation above the model estimate, say so and why.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as exc:
            fallback = self._fallback_explanation(
                patient_data, prob, feature_explanation, similar_cases, safety, evidence_status
            )
            return f"{fallback} LLM explanation unavailable: {exc}"

    def _fallback_explanation(
        self,
        patient_data,
        prob,
        feature_explanation=None,
        similar_cases=None,
        safety=None,
        evidence_status=None,
    ):
        bmi = patient_data["bmi"]
        features = (feature_explanation or {}).get("features", [])
        if features:
            driver_text = self._driver_text(feature_explanation)
        else:
            driver_text = self._threshold_text(patient_data)
        memory_text = ""
        if similar_cases:
            memory_text = (
                f"I found {len(similar_cases)} similar prior case(s) in memory; they are earlier"
                " model predictions, not confirmed outcomes."
            )

        return (
            f"The model estimated a {prob:.1%} risk using a calculated BMI of {bmi:.1f}. "
            f"{driver_text}{self._glucose_text(patient_data, feature_explanation)}"
            f"{self._defaults_text(patient_data)}{memory_text}"
            f"{self._safety_text(safety)}{self._evidence_text(evidence_status)}"
        )

    def _driver_text(self, feature_explanation):
        """Describe only what the model used; auto-filled inputs are not claimed as patient facts."""
        method = feature_explanation.get("method", "model").upper()
        features = [f for f in feature_explanation["features"] if not f.get("defaulted")]
        raising = [f["feature"] for f in features if f["direction"] == "raises risk"][:3]
        lowering = [f["feature"] for f in features if f["direction"] == "lowers risk"][:2]
        parts = []
        if raising:
            parts.append(f"raising risk: {', '.join(raising)}")
        if lowering:
            parts.append(f"lowering risk: {', '.join(lowering)}")
        if not parts:
            return f"The {method} explanation found no input with a notable effect. "
        return f"The {method} explanation shows {'; '.join(parts)}. "

    def _threshold_text(self, patient_data):
        """Used only when no model explanation is available: plain range checks, not model output."""
        notable = []
        if patient_data["age"] >= 55:
            notable.append("older age")
        if patient_data["bmi"] >= 30:
            notable.append("elevated BMI")
        if patient_data["bp"] >= 140:
            notable.append("high blood pressure")
        if not notable:
            return "No model explanation was available; the measured values are mostly in lower-risk ranges. "
        return f"No model explanation was available; values of note: {', '.join(notable)}. "

    def _glucose_text(self, patient_data, feature_explanation):
        not_in_model = (feature_explanation or {}).get("inputs_not_in_model", [])
        if "glucose" in not_in_model:
            return (
                f"Glucose ({patient_data['glucose']:.0f}) is not an input of this model; it is"
                " checked by the safety rules instead. "
            )
        if not patient_data.get("glucose_measured", True):
            return "Glucose was not measured, so the glucose rules could not be applied. "
        return ""

    def _defaults_text(self, patient_data):
        defaulted = patient_data.get("defaulted_fields", [])
        if not defaulted:
            return ""
        return (
            f"{len(defaulted)} optional input(s) were not provided and were filled with defaults. "
        )

    def _safety_text(self, safety):
        if not safety or not safety.get("alerts"):
            return ""
        text = f" Safety rules: {' '.join(safety['alerts'][:2])}"
        if safety.get("escalation", "routine_followup") != "routine_followup":
            text += f" Escalation: {safety['escalation']}."
        return text

    def _evidence_text(self, evidence_status):
        if evidence_status in ("none", "limited"):
            return f" Guideline evidence for this profile is {evidence_status}."
        return ""
