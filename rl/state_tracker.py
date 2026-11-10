"""Track model risk, evidence status and whether broader retrieval was used."""

from rl.environment import encode_state


class StateTracker:
    def __init__(self, risk, retrieved_more=False):
        self.risk = risk
        self.retrieved_more = retrieved_more
        self.evidence = "none"
        self.history = []

    def update(self, safety, evidence_status):
        """Refresh evidence; safety rules retain their separate escalation override."""
        self.evidence = evidence_status
        return self.state

    @property
    def state(self):
        return encode_state(self.risk, self.evidence, self.retrieved_more)

    def record(self, action):
        self.history.append(action)
        if action == "retrieve_more_evidence":
            self.retrieved_more = True

    def snapshot(self):
        return {
            "risk": self.risk,
            "evidence": self.evidence,
            "retrieved_more": self.retrieved_more,
            "actions": list(self.history),
        }
