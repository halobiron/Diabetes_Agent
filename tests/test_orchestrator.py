import pytest

from agents.explainer import ExplanationAgent
from agents.orchestrator import AGENT_VERSION, Orchestrator
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
STRONG = [{"relevance": 0.6, "text": "Test evidence.", "source_title": "ADA"}] * 2


class FakeModel:
    risk_bands = None
    decision_threshold = 0.3
    model_version = "t"
    artifact_metadata = {"selected_model": "fake"}

    def assess(self, data):
        return 0.6, {"age": 50, "bmi": 31.0, "bp": data["bp"]}


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

    def citation(self, evidence_id):
        return (
            {"evidence_id": evidence_id, "source_title": "ADA"} if evidence_id != "gone" else None
        )


class FakeWhatIf:
    def scenarios(self, patient):
        entry = {"key": "weight_loss", "change": -0.1, "evidence_ids": ["ev-1", "gone"]}
        return {"probability_before": 0.6, "scenarios": [entry], "combined": None}

    def most_informative_unknown(self, patient):
        return {
            "feature": "Smoker",
            "field": "smoker",
            "probability_if_no": 0.5,
            "probability_if_yes": 0.7,
            "swing": 0.2,
        }


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
    patient = {"age": 50, "bmi": 31.0, "bp": 190}
    safety = SafetyGuard().assess(patient, 0.6, "High", evidence_status="none")

    explanation = ExplanationAgent().explain(
        patient, 0.6, feature_explanation=FEATURES, safety=safety, evidence_status="none"
    )
    advice = RecommendationAgent().recommend(
        patient, "High", retrieved_context=[], safety=safety, feature_explanation=FEATURES
    )

    assert "Hướng xử trí: Khám bác sĩ khẩn cấp" in explanation
    assert "Bằng chứng hướng dẫn cho hồ sơ này: không có" in explanation
    assert "BMI, tăng huyết áp" in advice  # only the features that raise risk, in impact order


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
    assert any("chưa đầy đủ" in text for text in result["safety"]["disclaimers"])


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

    assert "khám bác sĩ" in result["recommendation"]
    assert set(components(result)) == {"recommender", "explainer"}


def test_policy_failure_keeps_prediction_and_urgent_safety_result():
    class BrokenPolicy:
        def decide(self, state):
            raise ConnectionError("policy unavailable")

    orchestrator, _ = build()
    orchestrator.support_policy = BrokenPolicy()
    result = orchestrator.run({"bp": 190})

    assert result["probability"] == 0.6
    assert result["safety"]["escalation"] == "urgent_clinician_review"
    assert result["policy"] is None
    assert components(result) == ["support_policy"]
    assert any("chưa đầy đủ" in text for text in result["safety"]["disclaimers"])


def test_counterfactuals_attach_citations_and_drive_the_followup():
    orchestrator, _ = build()
    orchestrator.what_if = FakeWhatIf()
    result = orchestrator.run({"bp": 120})

    scenario = result["what_if"]["scenarios"][0]
    assert scenario["evidence"] == [{"evidence_id": "ev-1", "source_title": "ADA"}]
    assert "evidence_ids" not in scenario
    assert result["followup"]["field"] == "smoker"
    assert [item["feature"] for item in result["evidence_trail"]] == ["BMI", "HighBP"]


def test_clinician_escalation_hides_what_if_and_extra_questions():
    orchestrator, _ = build()
    orchestrator.what_if = FakeWhatIf()
    result = orchestrator.run({"bp": 190})

    assert result["what_if"] is None and result["followup"] is None


def test_what_if_failure_degrades_instead_of_failing_the_request():
    class BrokenWhatIf:
        def scenarios(self, patient):
            raise RuntimeError("model unavailable")

    orchestrator, _ = build()
    orchestrator.what_if = BrokenWhatIf()
    result = orchestrator.run({"bp": 120})

    assert components(result) == ["what_if"]
    assert result["what_if"] is None and result["probability"] == 0.6


def test_trace_records_every_step_with_timing_and_outcome():
    orchestrator, _ = build()
    trace = orchestrator.run({"bp": 120})["trace"]

    assert [step["component"] for step in trace["steps"]] == [
        "risk_model",
        "feature_explainer",
        "memory_search",
        "retriever",
        "safety_guard",
        "recommender",
        "what_if",
        "explainer",
        "memory_store",
    ]
    assert all(step["status"] == "ok" and step["ms"] >= 0 for step in trace["steps"])
    assert trace["evidence_count"] == 2 and trace["evidence_status"] == "sufficient"
    assert trace["disagreement"] is None
    assert trace["total_ms"] >= sum(step["ms"] for step in trace["steps"]) * 0.99


def test_trace_marks_failed_step_with_its_fallback():
    orchestrator, _ = build(retriever=FakeRetriever(fail=True))
    steps = {step["component"]: step for step in orchestrator.run({"bp": 120})["trace"]["steps"]}

    assert steps["retriever"]["status"] == "degraded"
    assert steps["retriever"]["detail"] == "giữ các đoạn bằng chứng trước đó"
    assert steps["safety_guard"]["status"] == "ok"


def test_trace_reports_when_rules_override_the_model_risk():
    orchestrator, _ = build()
    trace = orchestrator.run({"bp": 190})["trace"]

    assert trace["disagreement"]["model_risk"] == "Medium"  # the fake model says 0.6
    assert trace["disagreement"]["effective_risk"] == "High"  # a measured BP of 190 overrides it
    assert [rule["code"] for rule in trace["disagreement"]["rules"]][0] == "BP-180"


def test_trace_carries_request_id_and_component_versions():
    orchestrator, _ = build()
    trace = orchestrator.run({"bp": 120}, request_id="req-123")["trace"]

    assert trace["request_id"] == "req-123"
    assert all(step["request_id"] == "req-123" for step in trace["steps"])
    steps = {step["component"]: step for step in trace["steps"]}
    assert steps["risk_model"]["version"] == "t"
    assert steps["safety_guard"]["version"] == AGENT_VERSION
    assert trace["versions"]["risk_model"] == "t"


def test_request_id_is_generated_when_not_given():
    orchestrator, _ = build()
    first = orchestrator.run({"bp": 120})["trace"]["request_id"]
    second = orchestrator.run({"bp": 120})["trace"]["request_id"]

    assert first and second and first != second
