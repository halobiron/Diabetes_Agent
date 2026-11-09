"""Q-learning policy, fixed baselines and evaluation for the support-step environment."""

import json
import random
from pathlib import Path

from rl.environment import ACTIONS, GLUCOSE, RISKS, SupportEnv, valid_actions

POLICY_VERSION = "support-policy-v2"


def _terminal_by_risk(state):
    risk, glucose = RISKS[state[0]], GLUCOSE[state[1]]
    if glucose == "elevated" or risk == "High":
        return "escalate_to_clinician"
    return "recommend_followup" if risk == "Medium" else "recommend_routine"


def fixed_risk_policy(state):
    """Current pipeline: no extra steps; advice level follows the risk band (and measured glucose)."""
    return _terminal_by_risk(state)


def fixed_full_policy(state):
    """Hand-written checklist: always gather what is missing, then answer by risk band."""
    actions = valid_actions(state)
    for step in ("request_glucose", "retrieve_more_evidence"):
        if step in actions:
            return step
    return _terminal_by_risk(state)


def make_random_policy(seed=0):
    rng = random.Random(seed)
    return lambda state: rng.choice(valid_actions(state))


def _key(state):
    return ",".join(str(part) for part in state)


class QPolicy:
    def __init__(self, q_table, metadata=None):
        self.q = q_table  # {state tuple: [value per action]}
        self.metadata = metadata or {}

    def q_values(self, state):
        return self.q.get(state)

    def __call__(self, state):
        return self.decide(state)["action"]

    def decide(self, state):
        """Best valid action by Q-value; unseen states fall back to the fixed checklist."""
        values = self.q_values(state)
        if values is None:
            return {"action": fixed_full_policy(state), "q_values": None, "source": "fallback"}
        valid = valid_actions(state)
        action = max(valid, key=lambda a: values[ACTIONS.index(a)])
        return {
            "action": action,
            "q_values": {a: round(values[ACTIONS.index(a)], 3) for a in valid},
            "source": "policy",
        }

    def save(self, path):
        payload = {
            "version": POLICY_VERSION,
            "actions": ACTIONS,
            "state_order": ["risk", "glucose", "evidence", "asked_glucose", "retrieved_more"],
            "q": {_key(state): [round(v, 5) for v in values] for state, values in self.q.items()},
            "metadata": self.metadata,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload["actions"] != ACTIONS:
            raise ValueError("Policy artifact was trained with a different action set.")
        q = {tuple(int(p) for p in key.split(",")): v for key, v in payload["q"].items()}
        return cls(q, {**payload.get("metadata", {}), "version": payload["version"]})


def train_q_learning(episodes=60000, alpha=0.1, epsilon_start=1.0, epsilon_end=0.05, seed=0):
    env = SupportEnv(seed)
    rng = random.Random(seed + 1)
    q = {}
    for episode in range(episodes):
        epsilon = max(epsilon_end, epsilon_start * (1 - episode / (0.8 * episodes)))
        state = env.reset()
        done = False
        while not done:
            values = q.setdefault(state, [0.0] * len(ACTIONS))
            valid = valid_actions(state)
            if rng.random() < epsilon:
                action = rng.choice(valid)
            else:
                action = max(valid, key=lambda a: values[ACTIONS.index(a)])
            next_state, reward, done, _ = env.step(action)
            target = reward
            if not done:
                next_values = q.setdefault(next_state, [0.0] * len(ACTIONS))
                target += max(next_values[ACTIONS.index(a)] for a in valid_actions(next_state))
            index = ACTIONS.index(action)
            values[index] += alpha * (target - values[index])
            state = next_state
    return QPolicy(
        q,
        {
            "algorithm": "tabular Q-learning",
            "episodes": episodes,
            "alpha": alpha,
            "gamma": 1.0,
            "seed": seed,
            "feedback": "simulated",
            "reward": "triage reward + entropy reduction",
        },
    )


def evaluate(policy, episodes=20000, seed=12345):
    """Mean reward (with 95% CI), steps and safety counts for `policy` on fresh episodes."""
    env = SupportEnv(seed)
    rewards, steps, under, over = [], 0, 0, 0
    for _ in range(episodes):
        state, total, done = env.reset(), 0.0, False
        while not done:
            action = policy(state)
            state, reward, done, info = env.step(action)
            total += reward
            steps += 1
        need = info["need"]
        if need == "escalate" and action != "escalate_to_clinician":
            under += 1
        elif need != "escalate" and action == "escalate_to_clinician":
            over += 1
        rewards.append(total)
    mean = sum(rewards) / episodes
    variance = sum((r - mean) ** 2 for r in rewards) / (episodes - 1)
    return {
        "episodes": episodes,
        "mean_reward": round(mean, 4),
        "ci95": round(1.96 * (variance / episodes) ** 0.5, 4),
        "mean_steps": round(steps / episodes, 3),
        "under_triage_rate": round(under / episodes, 4),
        "over_escalation_rate": round(over / episodes, 4),
    }
