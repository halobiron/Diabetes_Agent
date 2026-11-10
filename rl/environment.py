"""Simulated support-step environment using model risk and retrieved evidence.

Patient mix, broader-search success and rewards are project assumptions, not real
patient or clinician feedback. The state is (risk, evidence, retrieved_more).
A broader search can improve evidence once; terminal actions choose a support level.
"""

import random

RISKS = ["Low", "Medium", "High"]
EVIDENCE = ["none", "limited", "sufficient"]
ACTIONS = [
    "retrieve_more_evidence",
    "recommend_routine",
    "recommend_followup",
    "escalate_to_clinician",
]
TERMINAL_ACTIONS = ACTIONS[1:]

# Simulation assumptions.
RISK_PRIOR = [0.4, 0.35, 0.25]
EVIDENCE_PRIOR = [0.2, 0.4, 0.4]
P_BROADER_SEARCH_HELPS = 0.6  # evidence improves one level
STEP_COST = 0.05
EVIDENCE_BONUS = {"none": -0.2, "limited": 0.0, "sufficient": 0.2}  # non-escalation advice only

# REWARD[need][terminal action]: under-triage is penalised hardest, over-triage mildly.
REWARD = {
    "routine": {
        "recommend_routine": 1.0,
        "recommend_followup": -0.2,
        "escalate_to_clinician": -0.8,
    },
    "followup": {
        "recommend_routine": -0.5,
        "recommend_followup": 1.0,
        "escalate_to_clinician": -0.4,
    },
    "escalate": {
        "recommend_routine": -2.0,
        "recommend_followup": -2.0,
        "escalate_to_clinician": 1.0,
    },
}


def encode_state(risk, evidence, retrieved_more=False):
    return (RISKS.index(risk), EVIDENCE.index(evidence), int(retrieved_more))


def valid_actions(state):
    _, evidence, retrieved = state
    actions = []
    if EVIDENCE[evidence] != "sufficient" and not retrieved:
        actions.append("retrieve_more_evidence")
    return actions + TERMINAL_ACTIONS


def true_need(risk):
    if risk == "High":
        return "escalate"
    return "followup" if risk == "Medium" else "routine"


def terminal_reward(action, need, evidence):
    reward = REWARD[need][action]
    if action != "escalate_to_clinician":
        reward += EVIDENCE_BONUS[evidence]
    return reward


class SupportEnv:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def reset(self):
        rng = self.rng
        self.risk = rng.choices(RISKS, RISK_PRIOR)[0]
        self.evidence = rng.choices(EVIDENCE, EVIDENCE_PRIOR)[0]
        self.retrieved = False
        return self.state

    @property
    def state(self):
        return encode_state(self.risk, self.evidence, self.retrieved)

    def step(self, action):
        if action not in valid_actions(self.state):
            raise ValueError(f"Action {action!r} is not valid in state {self.state}")
        if action in TERMINAL_ACTIONS:
            need = true_need(self.risk)
            return self.state, terminal_reward(action, need, self.evidence), True, {"need": need}

        self.retrieved = True
        if self.rng.random() < P_BROADER_SEARCH_HELPS:
            self.evidence = EVIDENCE[min(EVIDENCE.index(self.evidence) + 1, 2)]
        return self.state, -STEP_COST, False, {}
