from types import SimpleNamespace

from agents.explainer import ExplanationAgent
from agents.llm_context import supplied_features, supplied_inputs, unknown_inputs
from agents.recommender import RecommendationAgent

# Prepared patient as RiskModel.assess returns it: only age, sex, height, weight and bp were
# given; the optional habits were filled with defaults.
PATIENT = {
    "age": 45,
    "height_cm": 160.0,
    "weight_kg": 55.0,
    "bmi": 21.5,
    "bp": 118,
    "high_bp": 0,
    "sex": 0,
    "phys_activity": 1,
    "smoker": 0,
    "high_chol": 0,
    "fruits": 1,
    "gen_hlth": 2,
    "defaulted_fields": ["PhysActivity", "Smoker", "HighChol", "Fruits", "GenHlth"],
    "skipped_fields": [],
    "optional_field_count": 18,
}
FEATURES = {
    "method": "sensitivity",
    "features": [
        {
            "feature": "BMI",
            "value": 21.5,
            "impact": -0.01,
            "direction": "lowers risk",
            "defaulted": False,
        },
        {
            "feature": "GenHlth",
            "value": 2,
            "impact": 0.02,
            "direction": "raises risk",
            "defaulted": True,
        },
    ],
}


class CapturingClient:
    """Stands in for OpenAI(): records the prompt and returns a fixed answer."""

    def __init__(self):
        self.prompts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages):
        self.prompts.append(messages[0]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])


def test_supplied_inputs_drop_defaults_and_bookkeeping():
    supplied = supplied_inputs(PATIENT)
    assert supplied["age"] == 45 and supplied["bp"] == 118 and supplied["sex"] == 0
    for key in ("phys_activity", "smoker", "high_chol", "fruits", "gen_hlth"):
        assert key not in supplied
    for key in ("defaulted_fields", "skipped_fields", "optional_field_count"):
        assert key not in supplied


def test_unknown_inputs_are_named_in_vietnamese():
    assert "vận động thể chất" in unknown_inputs(PATIENT)
    assert "hút thuốc" in unknown_inputs(PATIENT)


def test_supplied_features_drop_defaulted_features():
    assert [f["feature"] for f in supplied_features(FEATURES)["features"]] == ["BMI"]
    assert len(FEATURES["features"]) == 2  # input not modified


def _assert_prompt_hides_defaults(prompt):
    assert "'phys_activity'" not in prompt and "'smoker'" not in prompt
    assert "GenHlth" not in prompt.split("Inputs the patient did not supply")[0]
    assert "CHƯA trả lời" in prompt and "vận động thể chất" in prompt
    assert "'age': 45" in prompt


def test_recommendation_prompt_does_not_present_defaults_as_answers():
    agent = RecommendationAgent()
    agent.client = CapturingClient()
    agent.recommend(
        PATIENT, "Low", [], [], {"alerts": [], "escalation": "routine_followup"}, FEATURES
    )
    _assert_prompt_hides_defaults(agent.client.prompts[0])


def test_explanation_prompt_does_not_present_defaults_as_answers():
    agent = ExplanationAgent()
    agent.client = CapturingClient()
    agent.explain(PATIENT, 0.005, FEATURES, [], {"alerts": []}, "sufficient")
    prompt = agent.client.prompts[0]
    _assert_prompt_hides_defaults(prompt)
    assert "'GenHlth'" not in prompt
