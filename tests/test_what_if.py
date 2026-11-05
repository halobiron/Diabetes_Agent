from pathlib import Path

import pytest

from models.risk_model import RiskModel
from tools.explainability import evidence_trail
from tools.what_if import MIN_SWING, WhatIfSimulator

ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts" / "risk_model.joblib"


@pytest.fixture(scope="module")
def model():
    return RiskModel().load_artifact(ARTIFACT)


@pytest.fixture(scope="module")
def simulator(model):
    return WhatIfSimulator(model)


def prepare(model, **fields):
    base = {"age": 45, "height_cm": 170, "weight_kg": 95, "bp": 145}
    return model.prepare_patient({**base, **fields})


def test_scenarios_lower_risk_and_are_sorted_by_benefit(model, simulator):
    patient = prepare(model, smoker=True, phys_activity=False, high_chol=True)
    result = simulator.scenarios(patient)

    keys = [entry["key"] for entry in result["scenarios"]]
    assert {"weight_loss", "physical_activity", "smoking_cessation", "blood_pressure"} <= set(keys)
    changes = [entry["change"] for entry in result["scenarios"]]
    assert changes == sorted(changes) and all(change < 0 for change in changes)
    assert result["combined"]["probability_after"] < min(
        entry["probability_after"] for entry in result["scenarios"]
    )
    assert all(entry["evidence_ids"] for entry in result["scenarios"])


def test_weight_scenario_uses_five_percent_of_actual_weight(model, simulator):
    result = simulator.scenarios(prepare(model, weight_kg=100))
    weight = next(entry for entry in result["scenarios"] if entry["key"] == "weight_loss")
    assert "5% cân nặng" in weight["label"] and "5.0 kg" in weight["label"]


def test_scenarios_never_assume_unsupplied_habits(model, simulator):
    # Smoking and activity were left blank, so the model used defaults: nothing to "change".
    keys = {entry["key"] for entry in simulator.scenarios(prepare(model))["scenarios"]}
    assert not keys & {"physical_activity", "smoking_cessation"}


def test_no_scenario_for_already_healthy_inputs(model, simulator):
    patient = prepare(model, weight_kg=60, bp=110, smoker=False, phys_activity=True)
    assert simulator.scenarios(patient) == {
        "probability_before": pytest.approx(model.assess(patient)[0]),
        "scenarios": [],
        "combined": None,
    }


def test_most_informative_unknown_is_the_largest_swing(model, simulator):
    patient = prepare(model)
    best = simulator.most_informative_unknown(patient)

    assert best["swing"] >= MIN_SWING
    assert best["field"] in {"high_chol", "stroke", "heart_disease_or_attack", "diff_walk"}
    # Answering it removes it from the candidates.
    answered = prepare(model, **{best["field"]: False})
    again = simulator.most_informative_unknown(answered)
    assert again is None or again["field"] != best["field"]


def test_skipped_inputs_are_not_asked_again(model, simulator):
    patient = prepare(model)
    first = simulator.most_informative_unknown(patient)
    skipped = prepare(model, skipped_fields=[first["field"]])
    second = simulator.most_informative_unknown(skipped)
    assert second is None or second["field"] != first["field"]


def test_evidence_trail_links_drivers_to_their_own_passages_only():
    features = {
        "features": [
            {"feature": "BMI", "value": 31.0, "impact": 0.4},
            {"feature": "Smoker", "value": 0.0, "impact": 0.3, "defaulted": True},
            {"feature": "GenHlth", "value": 3.0, "impact": 0.2},
            {"feature": "PhysActivity", "value": 1.0, "impact": -0.1},
        ]
    }
    passages = [
        {"evidence_id": "a", "text": "t", "factors": ["BMI"], "relevance": 0.6},
        {"evidence_id": "b", "text": "u", "factors": ["Smoker"], "relevance": 0.5},
    ]
    trail = evidence_trail(features, passages)

    assert [item["feature"] for item in trail] == ["BMI", "GenHlth"]  # defaulted/lowering skipped
    assert [p["evidence_id"] for p in trail[0]["evidence"]] == ["a"]
    assert trail[1]["evidence"] == []
