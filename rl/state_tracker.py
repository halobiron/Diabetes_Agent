"""State tracker: one place that knows what the support policy can observe.

Borrowed from the hierarchical diagnosis design where a State Tracker turns the dialogue so
far into the state the main agent acts on. Here it gathers the model risk band, whether
glucose is measured/elevated, the evidence status, which information-gathering steps were
already taken, and how uncertain the true care need still is (entropy, in bits).
"""

from rl.environment import encode_state, need_entropy

ELEVATED_GLUCOSE_RULES = {"GLU-200", "GLU-300"}


class StateTracker:
    def __init__(self, patient, risk, retrieved_more=False):
        self.patient = patient
        self.risk = risk
        self.asked_glucose = bool(patient.get("glucose_unavailable", False))
        self.retrieved_more = retrieved_more
        self.glucose = "unmeasured"
        self.evidence = "none"
        self.history = []

    def update(self, safety, evidence_status):
        """Refresh from the latest rule results and evidence status; return the policy state."""
        self.evidence = evidence_status
        self.glucose = "unmeasured"
        if self.patient.get("glucose_measured", True):
            codes = {rule["code"] for rule in safety["rules"]}
            self.glucose = "elevated" if codes & ELEVATED_GLUCOSE_RULES else "normal"
        return self.state

    @property
    def state(self):
        return encode_state(
            self.risk, self.glucose, self.evidence, self.asked_glucose, self.retrieved_more
        )

    @property
    def uncertainty(self):
        """Remaining entropy (bits) about whether the patient needs escalation."""
        return need_entropy(self.risk, self.glucose)

    def record(self, action):
        self.history.append(action)
        if action == "retrieve_more_evidence":
            self.retrieved_more = True

    def snapshot(self):
        return {
            "risk": self.risk,
            "glucose": self.glucose,
            "evidence": self.evidence,
            "asked_glucose": self.asked_glucose,
            "retrieved_more": self.retrieved_more,
            "need_entropy_bits": round(self.uncertainty, 3),
            "actions": list(self.history),
        }
