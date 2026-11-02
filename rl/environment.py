"""Simulated environment for choosing the next support step.

There is NO real user or clinician feedback in this project. Everything below, including
patient mix, how often a patient supplies glucose, how often a broader search finds more
evidence, and the reward values, is a design assumption written down here. Policies
trained and compared on this environment show how they behave under these assumptions,
not how they would perform with real patients.

State (what the Orchestrator can observe):
    risk            model band: Low / Medium / High
    glucose         unmeasured / normal / elevated (measured >= 200 mg/dL)
    evidence        none / limited / sufficient (RetrievalAgent's evidence_status)
    asked_glucose   whether a glucose request was already made
    retrieved_more  whether a broadened evidence search was already done

Actions: two information-gathering steps (request glucose, retrieve more evidence) and
three terminal steps (routine advice, follow-up advice, escalate to a clinician).
"""

import random

RISKS = ["Low", "Medium", "High"]
GLUCOSE = ["unmeasured", "normal", "elevated"]
EVIDENCE = ["none", "limited", "sufficient"]
ACTIONS = [
    "request_glucose",
    "retrieve_more_evidence",
    "recommend_routine",
    "recommend_followup",
    "escalate_to_clinician",
]
TERMINAL_ACTIONS = ACTIONS[2:]

# Simulation assumptions.
RISK_PRIOR = [0.4, 0.35, 0.25]
P_ELEVATED_GIVEN_RISK = [0.1, 0.3, 0.6]  # chance the true glucose is >= 200 mg/dL
P_GLUCOSE_ALREADY_MEASURED = 0.5
EVIDENCE_PRIOR = [0.2, 0.4, 0.4]
P_PATIENT_SUPPLIES_GLUCOSE = 0.7
P_BROADER_SEARCH_HELPS = 0.6  # evidence improves one level
STEP_COST = 0.05
EVIDENCE_BONUS = {"none": -0.2, "limited": 0.0, "sufficient": 0.2}  # non-escalation advice only

NEEDS = ["routine", "followup", "escalate"]
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


def encode_state(risk, glucose, evidence, asked_glucose=False, retrieved_more=False):
    return (
        RISKS.index(risk),
        GLUCOSE.index(glucose),
        EVIDENCE.index(evidence),
        int(asked_glucose),
        int(retrieved_more),
    )


def valid_actions(state):
    _, glucose, evidence, asked, retrieved = state
    actions = []
    if GLUCOSE[glucose] == "unmeasured" and not asked:
        actions.append("request_glucose")
    if EVIDENCE[evidence] != "sufficient" and not retrieved:
        actions.append("retrieve_more_evidence")
    return actions + TERMINAL_ACTIONS


def true_need(risk, elevated):
    if elevated or risk == "High":
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
        self.elevated = rng.random() < P_ELEVATED_GIVEN_RISK[RISKS.index(self.risk)]
        measured = rng.random() < P_GLUCOSE_ALREADY_MEASURED
        self.glucose = ("elevated" if self.elevated else "normal") if measured else "unmeasured"
        self.evidence = rng.choices(EVIDENCE, EVIDENCE_PRIOR)[0]
        self.asked = False
        self.retrieved = False
        return self.state

    @property
    def state(self):
        return encode_state(self.risk, self.glucose, self.evidence, self.asked, self.retrieved)

    def step(self, action):
        if action not in valid_actions(self.state):
            raise ValueError(f"Action {action!r} is not valid in state {self.state}")
        if action in TERMINAL_ACTIONS:
            need = true_need(self.risk, self.elevated)
            return self.state, terminal_reward(action, need, self.evidence), True, {"need": need}

        if action == "request_glucose":
            self.asked = True
            if self.rng.random() < P_PATIENT_SUPPLIES_GLUCOSE:
                self.glucose = "elevated" if self.elevated else "normal"
        else:
            self.retrieved = True
            if self.rng.random() < P_BROADER_SEARCH_HELPS:
                self.evidence = EVIDENCE[min(EVIDENCE.index(self.evidence) + 1, 2)]
        return self.state, -STEP_COST, False, {}
