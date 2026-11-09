import pytest

from agents.advisor_agent import AdvisorAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.orchestrator import RunLog


class FakeModel:
    risk_bands = {"low_max": 0.2, "high_min": 0.4}
    decision_threshold = 0.25
    artifact_metadata = {"selected_model": "mlp"}
    model_version = "mlp-test"

    def assess(self, patient_data):
        return 0.5, {**patient_data, "bmi": 27}


class FakeExplainer:
    def explain(self, patient):
        return {"method": "sensitivity", "features": [{"feature": "BMI", "impact": 0.3}]}


class FakeRetriever:
    def __init__(self, passages=(), fail=False):
        self.passages, self.fail, self.calls = list(passages), fail, []

    def retrieve(self, patient, risk, feature_explanation, n_results=3, broaden=False):
        self.calls.append(broaden)
        if self.fail:
            raise RuntimeError("graph down")
        return self.passages


PASSAGE = {"evidence_id": "ev-1", "relevance": 0.8, "text": "t", "source_title": "s"}


def test_diagnosis_agent_calls_the_dl_model_and_traces_it():
    log = RunLog()
    result = DiagnosisAgent(FakeModel(), FakeExplainer()).diagnose({"age": 50}, log)

    assert result["probability"] == 0.5 and result["risk"] == "High"
    assert result["prediction"]["label"] == 1 and result["prediction"]["model"] == "mlp"
    assert result["feature_explanation"]["features"]
    assert [step["component"] for step in log.steps] == ["risk_model", "feature_explainer"]


def test_diagnosis_agent_degrades_explanation_but_not_the_model():
    class Broken:
        def explain(self, patient):
            raise RuntimeError("boom")

    log = RunLog()
    result = DiagnosisAgent(FakeModel(), Broken()).diagnose({"age": 50}, log)

    assert result["probability"] == 0.5
    assert result["feature_explanation"]["method"] == "none"
    assert [item["component"] for item in log.degraded] == ["feature_explainer"]


def test_diagnosis_agent_propagates_model_failure():
    class Down(FakeModel):
        def assess(self, patient_data):
            raise RuntimeError("Model unavailable")

    with pytest.raises(RuntimeError):
        DiagnosisAgent(Down()).diagnose({"age": 50}, RunLog())


def test_advisor_agent_retrieves_and_keeps_previous_evidence_on_failure():
    log = RunLog()
    ok = AdvisorAgent(FakeRetriever([PASSAGE]), None, None)
    assert ok.retrieve({}, "High", {}, log) == [PASSAGE]

    failing = AdvisorAgent(FakeRetriever(fail=True), None, None)
    assert failing.retrieve({}, "High", {}, log, previous=[PASSAGE]) == [PASSAGE]
    assert [item["component"] for item in log.degraded] == ["retriever"]


def test_advisor_agent_without_retriever_returns_previous():
    assert AdvisorAgent(None, None, None).retrieve({}, "Low", {}, RunLog(), previous=[PASSAGE]) == [
        PASSAGE
    ]


def test_trace_steps_name_the_owning_agent():
    log = RunLog()
    DiagnosisAgent(FakeModel(), FakeExplainer()).diagnose({"age": 50}, log)
    AdvisorAgent(FakeRetriever([PASSAGE]), None, None).retrieve({}, "High", {}, log)
    log.guard("safety_guard", lambda: None, None)

    assert {step["component"]: step["agent"] for step in log.steps} == {
        "risk_model": "diagnosis",
        "feature_explainer": "diagnosis",
        "retriever": "advisor",
        "safety_guard": "orchestrator",
    }
