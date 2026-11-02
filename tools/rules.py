"""Rule set for safety alerts and escalation.

Each rule has a code, a priority, a condition, an effect and a basis. Rules run in two
phases: *base* rules look at the patient's measurements, the model prediction and data
quality; *conflict* rules then look at how those results disagree with each other (and with
the retrieved evidence) and say how the disagreement is resolved.

Resolution policy, in order of precedence:
1. Measured values (BP, glucose) override the model prediction: a Low model risk never
   cancels a measured danger value, and the recommendation is written for `effective_risk`.
2. Escalation is the most severe level among fired rules; nothing lowers it, so missing
   guideline evidence or a reassuring prediction cannot downgrade an escalation.
3. A conflict never silently hides information: it is reported with its resolution.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

ESCALATION_LEVELS = ["routine_followup", "prompt_clinician_followup", "urgent_clinician_review"]
RISK_LEVELS = ["Low", "Medium", "High"]

HIGH_PROBABILITY = 0.85  # model probability treated as "very high predicted risk"
NORMAL_GLUCOSE_MAX = 100  # mg/dL; below this a measured glucose is not elevated


@dataclass
class RuleContext:
    patient: dict
    probability: float
    risk: str
    evidence_status: Optional[str] = None
    confidence_label: Optional[str] = None
    fired: dict = field(default_factory=dict)  # code -> Rule, filled between the two phases
    escalation: str = ESCALATION_LEVELS[0]

    @property
    def glucose_measured(self):
        return self.patient.get("glucose_measured", True)

    @property
    def glucose(self):
        return self.patient["glucose"] if self.glucose_measured else None

    def fired_category(self, category):
        return [rule for rule in self.fired.values() if rule.category == category]


@dataclass(frozen=True)
class Rule:
    code: str
    name: str
    category: str  # measurement | prediction | data_quality | conflict
    priority: int  # higher = more important; orders alerts
    condition: Callable[[RuleContext], bool]
    message: str
    basis: str
    escalation: Optional[str] = None  # level this rule requires, None = no change
    resolution: Optional[str] = None  # conflict rules: how the disagreement is settled

    def as_dict(self):
        item = {
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "priority": self.priority,
            "escalation": self.escalation,
            "message": self.message,
            "basis": self.basis,
        }
        if self.resolution:
            item["resolution"] = self.resolution
        return item


def _bp_between(low, high):
    return lambda ctx: low <= ctx.patient["bp"] < high


def _glucose_between(low, high):
    return lambda ctx: ctx.glucose is not None and low <= ctx.glucose < high


BASE_RULES = [
    Rule(
        code="GLU-300",
        name="Very high measured glucose",
        category="measurement",
        priority=100,
        condition=_glucose_between(300, float("inf")),
        message="Very high glucose value; urgent medical evaluation is recommended.",
        basis="Project threshold: measured glucose >= 300 mg/dL.",
        escalation="urgent_clinician_review",
    ),
    Rule(
        code="BP-180",
        name="Severely elevated blood pressure",
        category="measurement",
        priority=95,
        condition=_bp_between(180, float("inf")),
        message="Severely elevated blood pressure; urgent same-day clinical assessment is recommended.",
        basis="Project threshold: systolic BP >= 180 mmHg (ACC/AHA hypertensive-crisis range).",
        escalation="urgent_clinician_review",
    ),
    Rule(
        code="GLU-200",
        name="High measured glucose",
        category="measurement",
        priority=80,
        condition=_glucose_between(200, 300),
        message=(
            "High glucose value detected; prompt confirmatory testing and clinician review are"
            " recommended."
        ),
        basis="Project threshold: measured glucose 200-299 mg/dL (ADA: >= 200 mg/dL is in the diabetes range).",
        escalation="prompt_clinician_followup",
    ),
    Rule(
        code="BP-160",
        name="Very high blood pressure",
        category="measurement",
        priority=75,
        condition=_bp_between(160, 180),
        message="Very high blood pressure detected; prompt clinician follow-up is recommended.",
        basis="Project threshold: systolic BP 160-179 mmHg (ACC/AHA stage 2 hypertension or above).",
        escalation="prompt_clinician_followup",
    ),
    Rule(
        code="PRED-VERYHIGH",
        name="Very high predicted risk",
        category="prediction",
        priority=60,
        condition=lambda ctx: ctx.risk == "High" and ctx.probability >= HIGH_PROBABILITY,
        message="Model indicates very high predicted risk; expedited clinician review is advised.",
        basis=f"Project threshold: High risk band and model probability >= {HIGH_PROBABILITY}.",
        escalation="prompt_clinician_followup",
    ),
    Rule(
        code="DQ-GLU-MISSING",
        name="Glucose not measured",
        category="data_quality",
        priority=45,
        condition=lambda ctx: not ctx.glucose_measured,
        message="Glucose was not measured; risk estimate confidence is reduced.",
        basis="Glucose is not a BRFSS model input, so the estimate cannot be checked against a lab value.",
    ),
]

CONFLICT_RULES = [
    Rule(
        code="CF-PRED-LOW-MEASURED-HIGH",
        name="Low model risk vs dangerous measured value",
        category="conflict",
        priority=85,
        condition=lambda ctx: ctx.risk == "Low" and bool(ctx.fired_category("measurement")),
        message=(
            "Model risk is Low but a measured value is in a dangerous range; the measurement"
            " takes precedence over the model prediction."
        ),
        basis="Policy: measured clinical values override a statistical prediction.",
        resolution="measurement_overrides_prediction",
    ),
    Rule(
        code="CF-PRED-HIGH-GLUCOSE-NORMAL",
        name="High model risk vs normal measured glucose",
        category="conflict",
        priority=55,
        condition=lambda ctx: (
            ctx.risk == "High"
            and ctx.glucose is not None
            and ctx.glucose < NORMAL_GLUCOSE_MAX
            and not ctx.fired_category("measurement")
        ),
        message=(
            "Model flags High risk although the measured glucose is normal; a single normal"
            " value does not rule out risk, so the High risk is kept and an A1C test is advised."
        ),
        basis="Policy: a model-based risk is not downgraded by one normal glucose reading.",
        resolution="prediction_kept_confirm_with_a1c",
    ),
    Rule(
        code="CF-PRED-LOW-GLUCOSE-MISSING",
        name="Low model risk without glucose",
        category="conflict",
        priority=50,
        condition=lambda ctx: ctx.risk == "Low" and not ctx.glucose_measured,
        message=(
            "Low model risk is unconfirmed because glucose was not measured; do not treat it as"
            " reassurance until a glucose or A1C test is done."
        ),
        basis="Policy: absence of a measurement is not evidence of normal values.",
        resolution="prediction_unconfirmed_testing_advised",
    ),
    Rule(
        code="CF-PRED-HIGH-LOW-QUALITY",
        name="High model risk on low-quality data",
        category="conflict",
        priority=40,
        condition=lambda ctx: ctx.risk == "High" and ctx.confidence_label == "Low",
        message=(
            "High model risk rests on low-quality input data; treat it as provisional and"
            " confirm with measured values."
        ),
        basis="Policy: predictions made on implausible or missing inputs are provisional.",
        resolution="prediction_kept_marked_provisional",
    ),
    Rule(
        code="CF-ESCALATION-NO-EVIDENCE",
        name="Escalation without supporting guideline evidence",
        category="conflict",
        priority=30,
        condition=lambda ctx: (
            ctx.evidence_status in ("none", "limited")
            and ESCALATION_LEVELS.index(ctx.escalation) > 0
        ),
        message=(
            "Escalation is driven by the rules above, not by retrieved guideline text, which is"
            " missing or limited; the escalation is not lowered for lack of evidence."
        ),
        basis="Policy: safety escalation never depends on retrieval results.",
        resolution="escalation_kept_evidence_limited",
    ),
]

ALL_RULES = BASE_RULES + CONFLICT_RULES


def _max_level(levels, order):
    return max(levels, key=order.index, default=order[0])


class RuleEngine:
    def __init__(self, base_rules=None, conflict_rules=None):
        self.base_rules = BASE_RULES if base_rules is None else base_rules
        self.conflict_rules = CONFLICT_RULES if conflict_rules is None else conflict_rules
        codes = [rule.code for rule in self.base_rules + self.conflict_rules]
        if len(codes) != len(set(codes)):
            raise ValueError("Rule codes must be unique.")

    def evaluate(self, ctx):
        for rule in self.base_rules:
            if rule.condition(ctx):
                ctx.fired[rule.code] = rule
        ctx.escalation = _max_level(
            [r.escalation for r in ctx.fired.values() if r.escalation], ESCALATION_LEVELS
        )

        conflicts = []
        for rule in self.conflict_rules:
            if rule.condition(ctx):
                ctx.fired[rule.code] = rule
                conflicts.append(rule)

        # Measurements that demand escalation override a lower model risk for the advice.
        effective_risk = ctx.risk
        if ctx.fired_category("measurement"):
            effective_risk = _max_level([ctx.risk, "High"], RISK_LEVELS)

        fired = sorted(ctx.fired.values(), key=lambda r: r.priority, reverse=True)
        return {
            "escalation": ctx.escalation,
            "effective_risk": effective_risk,
            "alerts": [rule.message for rule in fired],
            "rules": [rule.as_dict() for rule in fired if rule.category != "conflict"],
            "conflicts": [rule.as_dict() for rule in fired if rule.category == "conflict"],
        }
