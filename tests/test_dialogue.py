from agents.dialogue import (
    RETRIEVE_MORE,
    conflict_exchanges,
    override_exchange,
    requested_actions,
)
from tests.test_orchestrator import STRONG, FakeRetriever, build

WEAK = [{"relevance": 0.35, "text": "Weak.", "source_title": "ADA"}]


class WideningRetriever(FakeRetriever):
    """Finds little on the first search and enough once asked to broaden."""

    def __init__(self, fail_on_broaden=False):
        super().__init__(contexts=WEAK)
        self.fail_on_broaden = fail_on_broaden
        self.calls = []

    def retrieve(self, patient, risk, features, n_results=3, broaden=False):
        self.calls.append(broaden)
        if broaden:
            if self.fail_on_broaden:
                raise RuntimeError("embedding service down")
            return STRONG
        return WEAK


def conflict(code):
    return {"code": code, "message": f"{code} message"}


def test_no_messages_when_components_agree():
    assert conflict_exchanges({"conflicts": []}) == []
    assert override_exchange(None) == []
    assert override_exchange({"steps": [], "overridden_by_rules": False}) == []


def test_measurement_beats_prediction_is_a_challenge_then_accept():
    messages = conflict_exchanges({"conflicts": [conflict("CF-PRED-LOW-MEASURED-HIGH")]})
    assert [m["performative"] for m in messages] == ["challenge", "accept"]
    assert (messages[0]["sender"], messages[0]["receiver"]) == ("safety_guard", "risk_model")
    assert (messages[1]["sender"], messages[1]["receiver"]) == ("risk_model", "safety_guard")
    assert all(m["rule"] == "CF-PRED-LOW-MEASURED-HIGH" for m in messages)
    assert requested_actions(messages) == []  # a concession asks for no work


def test_retriever_proposal_carries_an_action():
    messages = conflict_exchanges({"conflicts": [conflict("CF-ESCALATION-NO-EVIDENCE")]})
    assert [m["performative"] for m in messages] == ["challenge", "propose"]
    assert messages[0]["receiver"] == "retriever"
    assert requested_actions(messages) == [RETRIEVE_MORE]


def test_retriever_is_not_challenged_when_there_is_none():
    safety = {"conflicts": [conflict("CF-ESCALATION-NO-EVIDENCE")]}
    assert conflict_exchanges(safety, retriever_available=False) == []


def test_policy_override_is_challenged_and_accepted():
    policy = {"steps": [{"action": "recommend_routine"}], "overridden_by_rules": True}
    messages = override_exchange(policy)
    assert [m["performative"] for m in messages] == ["challenge", "accept"]
    assert messages[0]["receiver"] == "support_policy" and messages[0]["rule"] is None


def test_orchestrator_exposes_dialogue_without_adding_steps():
    orchestrator, _ = build()
    trace = orchestrator.run({"bp": 120})["trace"]
    assert trace["dialogue"] == []
    assert "dialogue" not in {step["component"] for step in trace["steps"]}


def test_the_proposal_changes_the_outcome_but_never_the_escalation():
    retriever = WideningRetriever()
    orchestrator, recorder = build(retriever=retriever)
    result = orchestrator.run({"bp": 190})

    assert retriever.calls == [False, True]  # searched once, then wider because it was proposed
    assert result["evidence_status"] == "sufficient"
    assert result["retrieved_context"] == STRONG
    assert (
        recorder.recommend_kwargs["retrieved_context"] == STRONG
    )  # advice rebuilt on new evidence
    assert result["safety"]["escalation"] == "urgent_clinician_review"  # never lowered
    assert result["safety"]["conflicts"] == []  # the evidence conflict is gone

    kinds = [(m["sender"], m["performative"]) for m in result["trace"]["dialogue"]]
    assert kinds == [
        ("safety_guard", "challenge"),
        ("retriever", "propose"),
        ("retriever", "inform"),
    ]
    assert result["trace"]["dialogue"][1]["action"] == RETRIEVE_MORE


def test_messages_say_where_in_the_step_trace_they_were_posted():
    orchestrator, _ = build(retriever=WideningRetriever())
    trace = orchestrator.run({"bp": 190})["trace"]
    steps = [step["component"] for step in trace["steps"]]
    challenge, proposal, outcome = trace["dialogue"]

    # challenge and proposal come after the first advice; the wider search is the next step
    assert challenge["after_step"] == proposal["after_step"]
    assert steps[challenge["after_step"] - 1] == "recommender"
    assert steps[challenge["after_step"]] == "retriever"
    # the result is reported after the advice was rebuilt on the new evidence
    assert outcome["after_step"] > proposal["after_step"]
    assert steps[outcome["after_step"] - 1] == "recommender"


def test_without_a_conflict_nothing_is_proposed_or_searched_again():
    retriever = WideningRetriever()
    orchestrator, _ = build(retriever=retriever)
    result = orchestrator.run({"bp": 120})  # routine: limited evidence is no conflict
    assert retriever.calls == [False]
    assert result["trace"]["dialogue"] == []


def test_failed_wider_search_keeps_earlier_evidence_and_says_so():
    retriever = WideningRetriever(fail_on_broaden=True)
    orchestrator, _ = build(retriever=retriever)
    result = orchestrator.run({"bp": 190})

    assert result["retrieved_context"] == WEAK
    assert result["safety"]["escalation"] == "urgent_clinician_review"
    assert [item["component"] for item in result["degraded"]] == ["retriever"]
    outcome = result["trace"]["dialogue"][-1]
    assert outcome["performative"] == "inform" and "lỗi" in outcome["content"]
