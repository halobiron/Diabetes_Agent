from tools.rules import RuleContext, RuleEngine


class SafetyGuard:
    def __init__(self, engine=None):
        self.engine = engine or RuleEngine()

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
            "disclaimers": disclaimers,
        }

    def _confidence(self, patient):
        # Simple reliability heuristic based on missingness and plausibility.
        score = 1.0
        if not patient.get("glucose_measured", True):
            score -= 0.25
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
