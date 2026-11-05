import numpy as np
import pytest

from models.risk_model import HIGH_BP_SYSTOLIC_CUTOFF, RiskModel
from models.training_pipeline import high_risk_cutoff
from tools.risk_classifier import classify_risk

BANDS = {"low_max": 0.26, "high_min": 0.5}


def test_classify_risk_uses_trained_bands():
    assert classify_risk(0.25, BANDS) == "Low"
    assert classify_risk(0.26, BANDS) == "Medium"  # binary threshold itself is flagged
    assert classify_risk(0.49, BANDS) == "Medium"
    assert classify_risk(0.5, BANDS) == "High"


def test_classify_risk_falls_back_to_legacy_cutoffs_without_bands():
    assert classify_risk(0.39) == "Low"
    assert classify_risk(0.4) == "Medium"
    assert classify_risk(0.7) == "High"


def test_binary_flag_never_labelled_low():
    # Anything at or above the binary threshold must not read as "Low".
    for prob in np.linspace(BANDS["low_max"], 1.0, 20):
        assert classify_risk(float(prob), BANDS) != "Low"


def test_high_risk_cutoff_requires_precision_above_low_max():
    y_true = np.array([0, 0, 0, 1, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.35, 0.4, 0.6, 0.7, 0.9])
    cutoff = high_risk_cutoff(y_true, y_prob, low_max=0.3, min_precision=0.75)
    assert cutoff is not None and cutoff > 0.3
    assert high_risk_cutoff(y_true, y_prob, low_max=0.95, min_precision=0.75) is None


@pytest.mark.parametrize(
    ("bp", "expected"),
    [(HIGH_BP_SYSTOLIC_CUTOFF - 1, 0), (HIGH_BP_SYSTOLIC_CUTOFF, 1), (180, 1)],
)
def test_systolic_bp_maps_to_high_bp(bp, expected):
    patient = RiskModel().prepare_patient({"age": 50, "bmi": 25, "bp": bp})
    assert patient["high_bp"] == expected


def test_explicit_high_bp_overrides_systolic_mapping():
    patient = RiskModel().prepare_patient({"age": 50, "bmi": 25, "bp": 120, "high_bp": True})
    assert patient["high_bp"] == 1
