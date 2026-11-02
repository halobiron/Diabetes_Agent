from tools.rules import RuleContext, RuleEngine


class SafetyGuard:
    def __init__(self, engine=None, max_defaulted_penalty=0.2):
        self.engine = engine or RuleEngine()
        self.max_defaulted_penalty = max_defaulted_penalty

    def assess(self, patient, probability, risk, evidence_status=None):
        confidence_score, confidence_label = self._confidence(patient)
        outcome = self.engine.evaluate(
            RuleContext(
                patient=patient,
                probability=probability,
                risk=risk,
                evidence_status=evidence_status,
                confidence_label=confidence_label,
            )
        )
        disclaimers = [
            "Educational prototype only; not a diagnostic medical device.",
            "Clinical decisions require clinician judgment and measured labs/vitals.",
        ]

        return {
            **outcome,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "confidence_note": (
                "Data-quality score from missing or implausible inputs; it is not a"
                " statistical confidence in the prediction."
            ),
            "defaulted_fields": list(patient.get("defaulted_fields", [])),
            "disclaimers": disclaimers,
        }

    def _confidence(self, patient):
        # Data-quality heuristic: missing glucose, auto-filled model inputs, implausible values.
        score = 1.0
        if not patient.get("glucose_measured", True):
            score -= 0.25
        # Scaled by the share of optional inputs auto-filled, so it does not depend on model size.
        optional = patient.get("optional_field_count", 0)
        if optional:
            share = len(patient.get("defaulted_fields", [])) / optional
            score -= self.max_defaulted_penalty * min(1.0, share)
        if patient["bp"] <= 70 or patient["bp"] >= 220:
            score -= 0.15
        if patient["bmi"] <= 14 or patient["bmi"] >= 50:
            score -= 0.1
        score = max(0.0, min(1.0, score))

        if score >= 0.85:
            label = "High"
        elif score >= 0.65:
            label = "Medium"
        else:
            label = "Low"
        return round(score, 2), label
