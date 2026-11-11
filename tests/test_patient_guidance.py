import pytest

from tools.patient_guidance import build_followup, measurement_scales


def patient(**changes):
    return {"age": 45, "bmi": 24.9, "bp": 120, **changes}


@pytest.mark.parametrize(
    "value,expected",
    [(18.49, "Thiếu cân"), (18.5, "Khoảng cân nặng khỏe mạnh"), (25, "Thừa cân"), (30, "Béo phì")],
)
def test_bmi_boundary_membership(value, expected):
    assert measurement_scales(patient(bmi=value))[0]["status"] == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (119, "Tâm thu dưới 120"),
        (120, "Tâm thu 120–129"),
        (140, "Tâm thu 140–179"),
        (180, "Tâm thu từ 180"),
    ],
)
def test_bp_boundary_membership(value, expected):
    assert measurement_scales(patient(bp=value))[1]["status"] == expected


def test_only_bmi_and_blood_pressure_are_displayed():
    assert [scale["key"] for scale in measurement_scales(patient())] == ["bmi", "bp"]


def test_missing_measurement_is_not_plotted():
    scale = measurement_scales(patient(bp=None))[1]
    assert scale["value"] is None
    assert scale["status"] == "Chưa có số đo"


def test_children_have_no_adult_reference_bands():
    scales = measurement_scales(patient(age=12))
    assert all(scale["bands"] == [] for scale in scales)
    assert measurement_scales(patient(age=19))[0]["bands"] == []


UNKNOWN = {
    "feature": "HighChol",
    "field": "high_chol",
    "probability_if_no": 0.06,
    "probability_if_yes": 0.16,
    "swing": 0.1,
}


def test_missing_model_input_is_asked_with_its_probability_range():
    asked = build_followup({"escalation": "routine_followup"}, unknown=UNKNOWN)
    assert asked["kind"] == "risk_factor" and asked["field"] == "high_chol"
    assert asked["source"] == "model_sensitivity"
    assert "6.0% đến 16.0%" in asked["reason"]


def test_no_question_when_nothing_is_missing():
    assert build_followup({"escalation": "routine_followup"}) is None


@pytest.mark.parametrize("escalation", ["prompt_clinician_followup", "urgent_clinician_review"])
def test_clinician_escalation_suppresses_the_model_input_question(escalation):
    assert build_followup({"escalation": escalation}, unknown=UNKNOWN) is None
