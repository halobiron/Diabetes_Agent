from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from agents.llm_context import supplied_inputs, unknown_inputs_instruction
from api.app import PatientRequest
from memory.profiles import editable_inputs
from models.symptoms import SYMPTOM_FIELDS, SymptomRiskModel, load_symptom_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def symptom_model():
    return SymptomRiskModel().load_artifact()


def payload():
    return {
        "age": 45,
        "bmi": 27,
        "bp": 130,
        "sex": "female",
        "screening_mode": "symptoms",
        "symptoms": {k: False for k in SYMPTOM_FIELDS},
    }


def test_unknown_symptom_is_not_silently_no():
    data = payload()
    data["symptoms"]["polyuria"] = None
    with pytest.raises(ValidationError):
        PatientRequest.model_validate(data)


@pytest.mark.parametrize("value", ["false", 0, 1])
def test_api_requires_actual_boolean_symptom_answers(value):
    data = payload()
    data["symptoms"]["polyuria"] = value
    with pytest.raises(ValidationError):
        PatientRequest.model_validate(data)


@pytest.mark.parametrize("age", [15, 91])
def test_symptom_model_does_not_extrapolate_age(age):
    with pytest.raises(ValidationError):
        PatientRequest.model_validate({**payload(), "age": age})


def test_symptoms_require_sex_and_reject_unknown_keys():
    with pytest.raises(ValidationError):
        PatientRequest.model_validate({**payload(), "sex": None})
    data = payload()
    data["symptoms"]["typo"] = False
    with pytest.raises(ValidationError):
        PatientRequest.model_validate(data)


def test_legacy_lifestyle_requests_remain_valid_without_symptoms():
    assert (
        PatientRequest.model_validate({"age": 45, "bmi": 27, "bp": 130}).screening_mode
        == "lifestyle"
    )


def test_data_deduplicated_before_split_and_no_profile_overlap(symptom_model):
    X, _, raw_count = load_symptom_data(ROOT / "data/train/symptoms/diabetes_data_upload.csv")
    assert raw_count == 520 and len(X) == 251
    meta = symptom_model.artifact_metadata
    train, val, test = [
        set(meta[k]) for k in ["train_indices", "validation_indices", "test_indices"]
    ]
    assert not train & test and not val & test and not train & val
    assert len(train | val | test) == len(X)


def test_raw_api_answers_match_training_columns_exactly(symptom_model):
    X, _, _ = load_symptom_data(ROOT / "data/train/symptoms/diabetes_data_upload.csv")
    for index in [0, 17, 70]:
        row = X.iloc[index]
        data = {
            **payload(),
            "age": int(row["age"]),
            "sex": "male" if row["Sex"] else "female",
            "symptoms": {k: bool(row[k]) for k in SYMPTOM_FIELDS},
        }
        probability, prepared = symptom_model.assess(data)
        expected = float(symptom_model.model.predict_proba(X.iloc[[index]])[0, 1])
        assert np.isclose(probability, expected)
        assert prepared["symptoms"] == data["symptoms"]
        assert prepared["defaulted_fields"] == []
        assert "high_chol" not in supplied_inputs(prepared)
        assert "không được suy diễn" in unknown_inputs_instruction(prepared)


def test_roundtrip_keeps_mode_and_all_symptoms(symptom_model):
    data = payload()
    _, patient = symptom_model.assess(data)
    restored = editable_inputs(patient)
    assert restored["screening_mode"] == "symptoms"
    assert restored["symptoms"] == data["symptoms"]


def test_standard_point_is_the_measured_approved_tradeoff(symptom_model):
    metadata = symptom_model.artifact_metadata
    assert metadata["selected_model"] == "random_forest"
    assert symptom_model.decision_threshold == 0.5
    assert metadata["test"]["confusion_matrix"] == {
        "true_negative": 12,
        "false_positive": 4,
        "false_negative": 3,
        "true_positive": 32,
    }
    assert "reused holdout" in metadata["test_status"]


def test_sensitivity_explains_integer_inputs_with_fractional_training_medians(symptom_model):
    from tools.explainability import FeatureExplainer

    _, patient = symptom_model.assess(payload())
    explanation = FeatureExplainer(symptom_model).explain(patient)
    assert len(explanation["features"]) == 16
    assert all(np.isfinite(f["impact"]) for f in explanation["features"])
