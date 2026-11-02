import pytest

from agents.explainer import ExplanationAgent
from agents.orchestrator import Orchestrator
from agents.recommender import RecommendationAgent
from tools.safety import SafetyGuard

FEATURES = {
    "method": "shap",
    "features": [
        {"feature": "BMI", "impact": 0.4, "direction": "raises risk"},
        {"feature": "HighBP", "impact": 0.2, "direction": "raises risk"},
        {"feature": "PhysActivity", "impact": -0.1, "direction": "lowers risk"},
    ],
}
STRONG = [{"relevance": 0.6, "text": "Test glucose.", "source_title": "ADA"}] * 2


class FakeModel:
    risk_bands = None
    decision_threshold = 0.3
    model_version = "t"
    artifact_metadata = {"selected_model": "fake"}

    def assess(self, data):
        return 0.6, {"age": 50, "bmi": 31.0, "bp": data["bp"], "glucose": 90.0}


class FakeMemory:
    def __init__(self, fail_search=False, fail_store=False):
        self.fail_search = fail_search
        self.fail_store = fail_store
        self.stored = []

    def find_similar(self, patient):
        if self.fail_search:
            raise RuntimeError("chroma down")
        return []

    def store(self, *args):
        if self.fail_store:
            raise RuntimeError("disk full")
        self.stored.append(args)


class FakeFeatureExplainer:
    def __init__(self, fail=False):
        self.fail = fail

    def explain(self, patient):
        if self.fail:
            raise RuntimeError("shap failed")
        return FEATURES


class FakeRetriever:
    def __init__(self, contexts=STRONG, fail=False):
        self.contexts = contexts
        self.fail = fail

    def retrieve(self, patient, risk, features, n_results=3, broaden=False):
        if self.fail:
            raise RuntimeError("embedding service down")
        return self.contexts


class Recorder:
    """Stands in for both text agents and records what the orchestrator handed them."""

    def __init__(self, fail=False):
        self.fail = fail
        self.explain_kwargs = None
        self.recommend_kwargs = None

    def explain(self, patient, prob, **kwargs):
        if self.fail:
            raise RuntimeError("llm down")
        self.explain_kwargs = kwargs
        return "explanation"

    def recommend(self, patient, risk, **kwargs):
        if self.fail:
            raise RuntimeError("llm down")
        self.recommend_kwargs = kwargs
        return "advice"


def build(recorder=None, memory=None, retriever=None, feature_explainer=None, guard=None):
    recorder = recorder or Recorder()
    return (
        Orchestrator(
            FakeModel(),
            recorder,
            recorder,
            memory or FakeMemory(),
            feature_explainer=feature_explainer or FakeFeatureExplainer(),
            retrieval_agent=retriever or FakeRetriever(),
            safety_guard=guard or SafetyGuard(),
        ),
        recorder,
    )


def components(result):
    return [item["component"] for item in result["degraded"]]


def test_agents_receive_each_others_results():
    orchestrator, recorder = build()
    result = orchestrator.run({"bp": 190})

    assert recorder.explain_kwargs["feature_explanation"] == FEATURES
    assert recorder.explain_kwargs["safety"] == result["safety"]
    assert recorder.explain_kwargs["evidence_status"] == "sufficient"
    assert recorder.recommend_kwargs["feature_explanation"] == FEATURES
    assert recorder.recommend_kwargs["retrieved_context"] == STRONG
    assert recorder.recommend_kwargs["safety"] == result["safety"]
    assert result["degraded"] == []


def test_fallback_texts_use_drivers_safety_and_evidence_status():
    patient = {"age": 50, "bmi": 31.0, "bp": 190, "glucose": 90.0}
    safety = SafetyGuard().assess(patient, 0.6, "High", evidence_status="none")

    explanation = ExplanationAgent().explain(
        patient, 0.6, feature_explanation=FEATURES, safety=safety, evidence_status="none"
    )
    advice = RecommendationAgent().recommend(
        patient, "High", retrieved_context=[], safety=safety, feature_explanation=FEATURES
    )

    assert "Escalation: urgent_clinician_review" in explanation
    assert "evidence for this profile is none" in explanation
    assert "BMI, HighBP" in advice  # only the features that raise risk, in impact order


@pytest.mark.parametrize(
    "kwargs, component",
    [
        ({"retriever": FakeRetriever(fail=True)}, "retriever"),
        ({"memory": FakeMemory(fail_search=True)}, "memory_search"),
        ({"memory": FakeMemory(fail_store=True)}, "memory_store"),
        ({"feature_explainer": FakeFeatureExplainer(fail=True)}, "feature_explainer"),
        ({"recorder": Recorder(fail=True)}, "explainer"),
    ],
)
def test_tool_failure_degrades_instead_of_failing_the_request(kwargs, component):
    orchestrator, _ = build(**kwargs)
    result = orchestrator.run({"bp": 120})

    assert component in components(result)
    assert result["probability"] == 0.6
    assert result["recommendation"] and result["explanation"]
    assert any("incomplete" in text for text in result["safety"]["disclaimers"])


def test_retriever_failure_reports_no_evidence():
    orchestrator, _ = build(retriever=FakeRetriever(fail=True))
    result = orchestrator.run({"bp": 120})

    assert result["retrieved_context"] == []
    assert result["evidence_status"] == "none"
    assert "RuntimeError: embedding service down" in result["degraded"][0]["error"]


def test_failed_safety_guard_fails_toward_clinician_review():
    class BrokenGuard:
        def assess(self, *args, **kwargs):
            raise RuntimeError("rules crashed")

    orchestrator, _ = build(guard=BrokenGuard())
    result = orchestrator.run({"bp": 120})

    assert "safety_guard" in components(result)
    assert result["safety"]["escalation"] == "prompt_clinician_followup"
    assert result["safety"]["confidence_label"] == "Low"


def test_text_agent_failure_uses_fixed_text():
    orchestrator, _ = build(recorder=Recorder(fail=True))
    result = orchestrator.run({"bp": 120})

    assert "consult a clinician" in result["recommendation"]
    assert set(components(result)) == {"recommender", "explainer"}
