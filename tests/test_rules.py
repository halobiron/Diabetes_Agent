import pytest

from tools.rules import ALL_RULES, ESCALATION_LEVELS, Rule, RuleContext, RuleEngine
from tools.safety import SafetyGuard


def patient(bp=120, bmi=25.0):
    return {"bp": bp, "bmi": bmi}


def assess(p, risk="Low", prob=0.1, evidence=None):
    return SafetyGuard().assess(p, prob, risk, evidence_status=evidence)


def codes(result, key="rules"):
    return {item["code"] for item in result[key]}


def test_rule_table_is_well_formed():
    assert len({rule.code for rule in ALL_RULES}) == len(ALL_RULES)
    for rule in ALL_RULES:
        assert rule.message and rule.basis and rule.name
        assert rule.escalation in (None, *ESCALATION_LEVELS)
        assert (rule.category == "conflict") == bool(rule.resolution)


def test_duplicate_codes_rejected():
    rule = ALL_RULES[0]
    with pytest.raises(ValueError):
        RuleEngine(base_rules=[rule, rule], conflict_rules=[])


@pytest.mark.parametrize(
    ("bp", "code", "level"),
    [
        (159, None, "routine_followup"),
        (160, "BP-160", "prompt_clinician_followup"),
        (179, "BP-160", "prompt_clinician_followup"),
        (180, "BP-180", "urgent_clinician_review"),
    ],
)
def test_measurement_thresholds(bp, code, level):
    result = assess(patient(bp), risk="High", prob=0.6)
    if code:
        assert code in codes(result)
    else:
        assert not codes(result) & {"BP-160", "BP-180"}
    assert result["escalation"] == level


def test_bp_bands_are_exclusive():
    assert codes(assess(patient(bp=185))) >= {"BP-180"}
    assert "BP-160" not in codes(assess(patient(bp=185)))


def test_escalation_is_most_severe_and_alerts_ordered_by_priority():
    result = assess(patient(bp=185), risk="High", prob=0.9)
    assert {"BP-180", "PRED-VERYHIGH"} <= codes(result)
    assert result["escalation"] == "urgent_clinician_review"
    priorities = [rule["priority"] for rule in result["rules"]]
    assert priorities == sorted(priorities, reverse=True)
    assert result["alerts"][0].startswith("Huyết áp tăng nghiêm trọng")


def test_very_high_prediction_escalates():
    result = assess(patient(), risk="High", prob=0.9)
    assert "PRED-VERYHIGH" in codes(result)
    assert result["escalation"] == "prompt_clinician_followup"
    assert "PRED-VERYHIGH" not in codes(assess(patient(), risk="High", prob=0.8))


def test_low_prediction_does_not_override_measurement():
    result = assess(patient(bp=165), risk="Low", prob=0.05)
    assert "CF-PRED-LOW-MEASURED-HIGH" in codes(result, "conflicts")
    assert result["escalation"] == "prompt_clinician_followup"
    assert result["effective_risk"] == "High"
    assert all(item["resolution"] for item in result["conflicts"])


def test_effective_risk_unchanged_without_measurement_rule():
    assert assess(patient(), risk="Medium", prob=0.4)["effective_risk"] == "Medium"
    assert assess(patient(), risk="Low", prob=0.1)["effective_risk"] == "Low"


def test_high_risk_on_low_quality_data_is_provisional():
    incomplete = {
        **patient(bp=225, bmi=55.0),
        "defaulted_fields": ["Smoker", "HighChol"],
        "optional_field_count": 2,
    }
    result = assess(incomplete, risk="High", prob=0.6)
    assert result["confidence_label"] == "Low"
    assert "CF-PRED-HIGH-LOW-QUALITY" in codes(result, "conflicts")


@pytest.mark.parametrize("evidence", ["none", "limited"])
def test_missing_evidence_never_lowers_escalation(evidence):
    result = assess(patient(bp=190), risk="High", prob=0.6, evidence=evidence)
    assert result["escalation"] == "urgent_clinician_review"
    assert "CF-ESCALATION-NO-EVIDENCE" in codes(result, "conflicts")


def test_sufficient_evidence_or_routine_has_no_evidence_conflict():
    assert "CF-ESCALATION-NO-EVIDENCE" not in codes(
        assess(patient(bp=190), risk="High", evidence="sufficient"), "conflicts"
    )
    assert "CF-ESCALATION-NO-EVIDENCE" not in codes(
        assess(patient(), risk="Low", evidence="none"), "conflicts"
    )


def test_custom_engine_rule_fires():
    rule = Rule(
        code="X-1",
        name="x",
        category="measurement",
        priority=1,
        condition=lambda ctx: ctx.patient["bp"] > 0,
        message="m",
        basis="b",
        escalation="urgent_clinician_review",
    )
    out = RuleEngine([rule], []).evaluate(RuleContext(patient(), 0.1, "Low"))
    assert out["escalation"] == "urgent_clinician_review"
    assert out["effective_risk"] == "High"
