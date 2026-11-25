import pytest

from agents.explainer import ExplanationAgent
from memory.context import describe_memory
from memory.store import MemoryAgent
from models.risk_model import RiskModel
from tools.explainability import FeatureExplainer
from tools.safety import SafetyGuard

FULL_BINARY = {
    "high_chol": 0,
    "chol_check": 1,
    "smoker": 0,
    "stroke": 0,
    "heart_disease_or_attack": 0,
    "phys_activity": 1,
    "fruits": 1,
    "veggies": 1,
    "heavy_alcohol_consump": 0,
    "any_healthcare": 1,
    "no_doc_bc_cost": 0,
    "diff_walk": 0,
    "gen_hlth": 2,
    "ment_hlth": 0,
    "phys_hlth": 0,
    "education": 5,
    "income": 6,
    "sex": 0,
}


@pytest.fixture(scope="module")
def model():
    from core.config import get_settings

    risk_model = RiskModel()
    risk_model.load_artifact(get_settings().model_artifact_path)
    return risk_model


def patient(age=50, bmi=27.0, bp=120, **extra):
    return {"age": age, "bmi": bmi, "bp": bp, **extra}


# ---- explanation matches the model's real inputs


def test_explanation_covers_only_model_inputs(model):
    prepared = model.prepare_patient({"age": 50, "bmi": 30, "bp": 150})
    explanation = FeatureExplainer(model).explain(prepared)

    assert explanation["inputs_not_in_model"] == []
    assert explanation["method_note"]
    assert {item["feature"] for item in explanation["features"]} <= set(model.feature_names)

    text = ExplanationAgent().explain(
        prepared, 0.3, feature_explanation=explanation, evidence_status="sufficient"
    )
    assert "không phải đầu vào của mô hình này" not in text


def test_zero_impact_feature_is_not_called_risk_lowering(model):
    prepared = model.prepare_patient({"age": 50, "bmi": 30, "bp": 150})
    explanation = FeatureExplainer(model).explain(prepared)

    for item in explanation["features"]:
        if item["magnitude"] == 0:
            assert item["direction"] == "no effect"


def test_explanation_does_not_claim_defaulted_inputs(model):
    prepared = model.prepare_patient({"age": 50, "bmi": 30, "bp": 150})
    explanation = FeatureExplainer(model).explain(prepared)
    flagged = {item["feature"] for item in explanation["features"] if item["defaulted"]}
    assert "HighChol" in flagged and "BMI" not in flagged

    features = [
        {"feature": "HighChol", "direction": "raises risk", "defaulted": True},
        {"feature": "BMI", "direction": "raises risk", "defaulted": False},
    ]
    text = ExplanationAgent()._driver_text({"method": "sensitivity", "features": features})
    assert "BMI" in text and "HighChol" not in text


# ---- confidence is a data-quality score that counts auto-filled fields


def test_defaulted_fields_lower_the_data_quality_score(model):
    guard = SafetyGuard()
    complete = model.prepare_patient({"age": 50, "bmi": 27, "bp": 120, **FULL_BINARY})
    minimal = model.prepare_patient({"age": 50, "bmi": 27, "bp": 120})

    assert complete["defaulted_fields"] == []
    assert len(minimal["defaulted_fields"]) > 10

    full = guard.assess(complete, 0.1, "Low")
    sparse = guard.assess(minimal, 0.1, "Low")
    assert full["confidence_score"] == 1.0
    assert sparse["confidence_score"] < full["confidence_score"]
    assert sparse["defaulted_fields"] == minimal["defaulted_fields"]
    assert "không phải độ tin cậy thống kê" in sparse["confidence_note"]


def test_penalty_scales_with_share_of_defaulted_inputs():
    guard = SafetyGuard(max_defaulted_penalty=0.2)
    base = patient()
    everything = {**base, "defaulted_fields": list("abcd"), "optional_field_count": 4}
    half = {**base, "defaulted_fields": list("ab"), "optional_field_count": 4}

    assert guard.assess(everything, 0.1, "Low")["confidence_score"] == 0.8
    assert guard.assess(half, 0.1, "Low")["confidence_score"] == 0.9
    assert (
        SafetyGuard(max_defaulted_penalty=0.0).assess(everything, 0.1, "Low")["confidence_score"]
        == 1.0
    )


def test_input_spreads_come_from_training_data(model):
    spreads = model.input_spreads()
    assert spreads["bmi"] == pytest.approx(float(model.training_frame["BMI"].std()))
    assert spreads["age"] == pytest.approx(float(model.training_frame["Age"].std()) * 5)
    assert "bp" not in spreads


# ---- history: same patient, latest assessment, predictions are not outcomes


@pytest.fixture
def memory(tmp_path):
    return MemoryAgent(str(tmp_path / "chroma"))


def test_history_uses_latest_assessment_of_same_patient(memory):
    old = memory.store(patient(patient_id="a", bmi=30), 0.4, "Medium")
    latest = memory.store(patient(patient_id="a", bmi=29), 0.3, "Medium")
    memory.store(patient(patient_id="b", bmi=40), 0.8, "High")
    memory.collection.update(ids=[old], metadatas=[{"timestamp": "2025-01-01T00:00:00+00:00"}])
    memory.collection.update(ids=[latest], metadatas=[{"timestamp": "2025-02-01T00:00:00+00:00"}])
    context = memory.recall(patient(patient_id="a", bmi=28, bp=115), 0.2, "Low", "v1")
    assert context["previous"]["id"] == latest
    assert context["assessment_count"] == 2
    assert "BMI từ 29 thành 28" in describe_memory(context)
    assert "Huyết áp tâm thu từ 120 thành 115" in describe_memory(context)


def test_new_profile_does_not_use_unlinked_or_other_patient_records(memory):
    memory.store(patient(bmi=30), 0.4, "Medium")  # legacy record without a profile ID
    memory.store(patient(patient_id="other", bmi=30), 0.4, "Medium")
    assert (
        memory.recall(patient(patient_id="new"), 0.2, "Low", "v1")["status"] == "first_assessment"
    )
    assert len(memory.get_all()) == 2  # old records remain intact


def test_stored_cases_are_labelled_as_predictions(memory):
    memory.store(patient(age=58, bmi=31.0, bp=140), 0.4, "Medium")
    metadata = memory.get_all()[0]["metadata"]

    assert metadata["outcome_confirmed"] is False
