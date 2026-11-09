import pytest

from agents.orchestrator import Orchestrator
from rl.environment import (
    ACTIONS,
    REWARD,
    TERMINAL_ACTIONS,
    SupportEnv,
    encode_state,
    terminal_reward,
    true_need,
    valid_actions,
)
from rl.policy import (
    QPolicy,
    evaluate,
    fixed_full_policy,
    fixed_risk_policy,
    make_random_policy,
    train_q_learning,
)


def test_valid_actions_mask_unavailable_steps():
    unmeasured = encode_state("Medium", "unmeasured", "limited")
    assert set(valid_actions(unmeasured)) == set(ACTIONS)

    done_all = encode_state("Medium", "normal", "sufficient", asked_glucose=True)
    assert valid_actions(done_all) == TERMINAL_ACTIONS
    assert "request_glucose" not in valid_actions(encode_state("Low", "normal", "none"))
    assert "retrieve_more_evidence" not in valid_actions(
        encode_state("Low", "unmeasured", "none", retrieved_more=True)
    )


def test_reward_penalises_under_triage_more_than_over_triage():
    assert true_need("Low", elevated=True) == "escalate"
    assert true_need("High", elevated=False) == "escalate"
    assert true_need("Medium", elevated=False) == "followup"
    for need in REWARD:
        assert (
            max(REWARD[need], key=REWARD[need].get)
            == {
                "routine": "recommend_routine",
                "followup": "recommend_followup",
                "escalate": "escalate_to_clinician",
            }[need]
        )
    assert terminal_reward("recommend_routine", "escalate", "sufficient") < terminal_reward(
        "escalate_to_clinician", "routine", "sufficient"
    )


def test_environment_is_reproducible_and_rejects_invalid_actions():
    first, second = SupportEnv(7), SupportEnv(7)
    assert first.reset() == second.reset()
    assert first.step("recommend_followup") == second.step("recommend_followup")

    env = SupportEnv(1)
    env.reset()
    env.glucose = "normal"
    with pytest.raises(ValueError):
        env.step("request_glucose")


def test_episodes_terminate_within_three_steps():
    env = SupportEnv(3)
    for _ in range(200):
        state, done, steps = env.reset(), False, 0
        while not done:
            state, _, done, _ = env.step(fixed_full_policy(state))
            steps += 1
        assert steps <= 3


@pytest.fixture(scope="module")
def trained():
    return train_q_learning(episodes=20000, seed=0)


def test_trained_policy_beats_random_and_risk_only(trained):
    learned = evaluate(trained, episodes=4000)
    assert learned["mean_reward"] > evaluate(make_random_policy(), episodes=4000)["mean_reward"]
    assert learned["mean_reward"] > evaluate(fixed_risk_policy, episodes=4000)["mean_reward"]


def test_trained_policy_gathers_glucose_for_ambiguous_patients(trained):
    state = encode_state("Medium", "unmeasured", "sufficient")
    assert trained.decide(state)["action"] == "request_glucose"
    assert trained.decide(encode_state("Low", "normal", "sufficient"))["action"] == (
        "recommend_routine"
    )


def test_policy_round_trip_and_fallback(trained, tmp_path):
    path = tmp_path / "policy.json"
    trained.save(path)
    loaded = QPolicy.load(path)
    state = encode_state("High", "unmeasured", "none")
    assert loaded.decide(state) == trained.decide(state)

    empty = QPolicy({})
    decision = empty.decide(state)
    assert decision["source"] == "fallback" and decision["q_values"] is None


class FakeModel:
    risk_bands = None
    decision_threshold = 0.3
    model_version = "t"
    artifact_metadata = {"selected_model": "fake"}

    def assess(self, data):
        return 0.1, {**data, "glucose_measured": False, "bp": data["bp"], "glucose": 90.0}


class FakeMemory:
    def find_similar(self, patient):
        return []

    def store(self, *args):
        pass


class FakeAgent:
    def explain(self, *args, **kwargs):
        return "x"

    def recommend(self, *args, **kwargs):
        return "advice"


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, patient, risk, features, n_results=3, broaden=False):
        self.calls.append(broaden)
        return [] if not broaden else [{"relevance": 0.6}, {"relevance": 0.5}]


class FixedPolicy:
    metadata = {"version": "fixed"}

    def __init__(self, *actions):
        self.actions = list(actions)

    def decide(self, state):
        return {"action": self.actions.pop(0), "q_values": None, "source": "policy"}


def make_orchestrator(policy, safety_guard=None):
    agent = FakeAgent()
    retriever = FakeRetriever()
    orchestrator = Orchestrator(
        FakeModel(), agent, agent, FakeMemory(), retrieval_agent=retriever, support_policy=policy
    )
    orchestrator.safety_guard = safety_guard
    return orchestrator, retriever


def test_orchestrator_acts_on_retrieve_more_then_stops():
    orchestrator, retriever = make_orchestrator(
        FixedPolicy("retrieve_more_evidence", "recommend_routine")
    )
    result = orchestrator.run({"bp": 120})

    assert retriever.calls == [False, True]
    assert result["evidence_status"] == "sufficient"
    assert result["policy"]["next_step"] == "recommend_routine"
    assert result["policy"]["steps"][0]["evidence_status_after"] == "sufficient"


def test_rules_override_policy_that_under_triages():
    from tools.safety import SafetyGuard

    class Guard(SafetyGuard):
        def assess(self, patient, probability, risk, evidence_status=None):
            return {**super().assess(patient, probability, risk, evidence_status)}

    orchestrator, _ = make_orchestrator(FixedPolicy("recommend_routine"), Guard())
    result = orchestrator.run({"bp": 190, "bmi": 25.0})

    assert result["safety"]["escalation"] == "urgent_clinician_review"
    assert result["policy"]["overridden_by_rules"] is True
    assert result["policy"]["next_step"] == "escalate_to_clinician"


def test_no_policy_means_no_policy_block():
    orchestrator, retriever = make_orchestrator(None)
    assert orchestrator.run({"bp": 120})["policy"] is None
    assert retriever.calls == [False]


def test_need_entropy_is_zero_once_known_and_positive_when_ambiguous():
    from rl.environment import need_entropy

    assert need_entropy("High", "unmeasured") == 0.0
    assert need_entropy("Medium", "normal") == 0.0
    assert need_entropy("Low", "unmeasured") > 0
    assert need_entropy("Medium", "unmeasured") > need_entropy("Low", "unmeasured")


def test_glucose_request_reward_includes_entropy_reduction():
    from rl.environment import ENTROPY_WEIGHT, STEP_COST

    env = SupportEnv(0)
    env.reset()
    env.risk, env.glucose, env.asked, env.elevated = "Medium", "unmeasured", False, False
    env.rng.random = lambda: 0.0  # patient supplies glucose
    _, reward, done, info = env.step("request_glucose")
    assert not done and info["entropy_reduction"] > 0
    assert reward == pytest.approx(-STEP_COST + ENTROPY_WEIGHT * info["entropy_reduction"])

    env.rng.random = lambda: 0.99  # patient does not supply it
    env.risk, env.glucose, env.asked = "Medium", "unmeasured", False
    _, reward, _, info = env.step("request_glucose")
    assert info["entropy_reduction"] == 0 and reward == pytest.approx(-STEP_COST)


def test_state_tracker_builds_state_and_records_history():
    from rl.state_tracker import StateTracker

    tracker = StateTracker({"glucose_measured": False}, "Medium")
    state = tracker.update({"rules": []}, "limited")
    assert state == encode_state("Medium", "unmeasured", "limited")
    assert tracker.uncertainty > 0

    tracker.record("retrieve_more_evidence")
    elevated = tracker.update({"rules": [{"code": "GLU-200"}]}, "sufficient")
    assert elevated == encode_state("Medium", "unmeasured", "sufficient", retrieved_more=True)

    measured = StateTracker({"glucose_measured": True}, "Low")
    assert measured.update({"rules": [{"code": "GLU-300"}]}, "none") == encode_state(
        "Low", "elevated", "none"
    )
    snap = measured.snapshot()
    assert snap["need_entropy_bits"] == 0 and snap["actions"] == []
