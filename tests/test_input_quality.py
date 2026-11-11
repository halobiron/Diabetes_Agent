import pytest

from tools.safety import SafetyGuard


def assess(**overrides):
    patient = {"bp": 130, "bmi": 28.5}
    return SafetyGuard().assess({**patient, **overrides}, 0.1, "Low")


def test_normal_input_does_not_request_confirmation():
    result = assess()
    assert result["confidence_score"] == 1.0
    assert result["confidence_reasons"] == []


@pytest.mark.parametrize("bp,bmi", [(70, 14), (220, 50)])
def test_75_points_explains_both_measurement_deductions(bp, bmi):
    result = assess(bp=bp, bmi=bmi)
    assert result["confidence_score"] == 0.75
    reasons = result["confidence_reasons"]
    assert {r["code"] for r in reasons} == {
        "bp_outside_check_range", "bmi_outside_check_range"
    }
    assert sum(r["penalty"] for r in reasons) == pytest.approx(0.25)
    assert str(bp) in reasons[0]["message"]
    assert str(bmi) in reasons[1]["message"]


def test_missing_inputs_explain_scaled_deduction_and_exact_fields():
    result = assess(defaulted_fields=["HighChol", "Smoker"], optional_field_count=4)
    assert result["confidence_score"] == 0.9
    assert result["confidence_reasons"][0]["fields"] == ["HighChol", "Smoker"]
    assert result["confidence_reasons"][0]["penalty"] == pytest.approx(0.1)


def test_mixed_reasons_reconcile_with_score_and_keep_safety_alerts():
    result = assess(bp=220, bmi=50, defaulted_fields=["Smoker"], optional_field_count=4)
    assert result["confidence_score"] == 0.7
    assert len(result["confidence_reasons"]) == 3
    assert result["escalation"] == "urgent_clinician_review"
    assert result["alerts"]


def test_custom_default_penalty_still_matches_explanation():
    result = SafetyGuard(max_defaulted_penalty=0.4).assess(
        {"bp": 130, "bmi": 28.5,
         "defaulted_fields": ["Smoker"], "optional_field_count": 2},
        0.1,
        "Low",
    )
    assert result["confidence_score"] == 0.8
    assert result["confidence_reasons"][0]["penalty"] == pytest.approx(0.2)
