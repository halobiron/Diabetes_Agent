import pytest

from tools.patient_guidance import build_followup, measurement_scales


def patient(**changes):
    return {"age": 45, "bmi": 24.9, "bp": 120, "glucose": 110, "glucose_measured": True, **changes}


@pytest.mark.parametrize(
    "value,expected",
    [(18.49, "Thiếu cân"), (18.5, "Khoảng cân nặng khỏe mạnh"), (25, "Thừa cân"), (30, "Béo phì")],
)
def test_bmi_boundary_membership(value, expected):
    assert measurement_scales(patient(bmi=value))[0]["status"] == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (69.9, "Dưới 70: đường huyết thấp"),
        (70, "70 đến dưới 100"),
        (99.9, "70 đến dưới 100"),
        (100, "100 đến dưới 126"),
        (125.9, "100 đến dưới 126"),
        (126, "Từ 126: cần xác nhận"),
    ],
)
def test_fasting_glucose_boundaries(value, expected):
    assert (
        measurement_scales(patient(glucose=value, glucose_context="fasting"))[2]["status"]
        == expected
    )


@pytest.mark.parametrize("context", ["unspecified", "unknown", "random", "after_meal"])
def test_no_fasting_bands_for_other_contexts(context):
    scale = measurement_scales(patient(glucose=90, glucose_context=context))[2]
    assert scale["bands"] == []
    assert scale["tone"] == "neutral"


def test_missing_glucose_does_not_plot_imputed_value():
    scale = measurement_scales(patient(glucose=999, glucose_measured=False))[2]
    assert scale["value"] is None
    assert scale["status"] == "Chưa có số đo"


def test_children_have_no_adult_reference_bands():
    scales = measurement_scales(patient(age=12, glucose_context="fasting"))
    assert all(scale["bands"] == [] for scale in scales)
    assert measurement_scales(patient(age=19))[0]["bands"] == []


def test_followup_distinguishes_policy_from_data_quality():
    safety = {"escalation": "routine_followup"}
    missing = patient(glucose_measured=False)
    assert build_followup(missing, safety, {"next_step": "request_glucose"})["source"] == "policy"
    assert build_followup(missing, safety)["source"] == "data_quality"
    # The measurement context is collected by the form, never asked as a follow-up.
    assert build_followup(patient(), safety) is None


def test_decline_or_known_unknown_prevents_repeated_question():
    safety = {"escalation": "routine_followup"}
    assert build_followup(patient(glucose_measured=False, glucose_unavailable=True), safety) is None
    assert build_followup(patient(glucose_context="unknown"), safety) is None


@pytest.mark.parametrize("escalation", ["prompt_clinician_followup", "urgent_clinician_review"])
def test_clinician_review_takes_precedence_over_questions(escalation):
    assert build_followup(patient(glucose_measured=False), {"escalation": escalation}) is None


UNKNOWN = {
    "feature": "HighChol",
    "field": "high_chol",
    "probability_if_no": 0.06,
    "probability_if_yes": 0.16,
    "swing": 0.1,
}


def test_missing_model_input_is_asked_only_after_glucose():
    safety = {"escalation": "routine_followup"}
    asked = build_followup(patient(), safety, unknown=UNKNOWN)
    assert asked["kind"] == "risk_factor" and asked["field"] == "high_chol"
    assert "6.0% đến 16.0%" in asked["reason"]
    # Glucose drives the safety rules, so it still comes first when missing...
    missing = patient(glucose_measured=False)
    assert build_followup(missing, safety, unknown=UNKNOWN)["kind"] == "glucose"
    # ...but not once the user has declined to provide it.
    declined = patient(glucose_measured=False, glucose_unavailable=True)
    assert build_followup(declined, safety, unknown=UNKNOWN)["kind"] == "risk_factor"


def test_clinician_escalation_suppresses_the_model_input_question():
    assert build_followup(patient(), {"escalation": "urgent_clinician_review"}, unknown=UNKNOWN) is None
