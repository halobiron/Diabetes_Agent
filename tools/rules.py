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
        name="Đường huyết đo được rất cao",
        category="measurement",
        priority=100,
        condition=_glucose_between(300, float("inf")),
        message="Đường huyết rất cao; cần được đánh giá y tế khẩn cấp.",
        basis="Ngưỡng của dự án: đường huyết đo được >= 300 mg/dL.",
        escalation="urgent_clinician_review",
    ),
    Rule(
        code="BP-180",
        name="Huyết áp tăng nghiêm trọng",
        category="measurement",
        priority=95,
        condition=_bp_between(180, float("inf")),
        message="Huyết áp tăng nghiêm trọng; cần khám khẩn trong ngày.",
        basis="Ngưỡng của dự án: huyết áp tâm thu >= 180 mmHg (khoảng cơn tăng huyết áp theo ACC/AHA).",
        escalation="urgent_clinician_review",
    ),
    Rule(
        code="GLU-200",
        name="Đường huyết đo được cao",
        category="measurement",
        priority=80,
        condition=_glucose_between(200, 300),
        message=("Phát hiện đường huyết cao; cần sớm xét nghiệm xác nhận và khám bác sĩ."),
        basis="Ngưỡng của dự án: đường huyết đo được 200–299 mg/dL (ADA: từ 200 mg/dL thuộc khoảng đái tháo đường).",
        escalation="prompt_clinician_followup",
    ),
    Rule(
        code="BP-160",
        name="Huyết áp rất cao",
        category="measurement",
        priority=75,
        condition=_bp_between(160, 180),
        message="Phát hiện huyết áp rất cao; cần sớm khám bác sĩ.",
        basis="Ngưỡng của dự án: huyết áp tâm thu 160–179 mmHg (tăng huyết áp giai đoạn 2 trở lên theo ACC/AHA).",
        escalation="prompt_clinician_followup",
    ),
    Rule(
        code="PRED-VERYHIGH",
        name="Nguy cơ dự đoán rất cao",
        category="prediction",
        priority=60,
        condition=lambda ctx: ctx.risk == "High" and ctx.probability >= HIGH_PROBABILITY,
        message="Mô hình dự đoán nguy cơ rất cao; nên sớm được bác sĩ đánh giá.",
        basis=f"Ngưỡng của dự án: mức nguy cơ Cao và xác suất mô hình >= {HIGH_PROBABILITY}.",
        escalation="prompt_clinician_followup",
    ),
]

CONFLICT_RULES = [
    Rule(
        code="CF-PRED-LOW-MEASURED-HIGH",
        name="Mô hình dự đoán thấp nhưng số đo nguy hiểm",
        category="conflict",
        priority=85,
        condition=lambda ctx: ctx.risk == "Low" and bool(ctx.fired_category("measurement")),
        message=(
            "Mô hình dự đoán nguy cơ thấp nhưng số đo nằm trong khoảng nguy hiểm; ưu tiên số đo thực tế hơn dự đoán."
        ),
        basis="Nguyên tắc: số đo lâm sàng thực tế được ưu tiên hơn dự đoán thống kê.",
        resolution="measurement_overrides_prediction",
    ),
    Rule(
        code="CF-PRED-HIGH-GLUCOSE-NORMAL",
        name="Mô hình dự đoán cao nhưng đường huyết bình thường",
        category="conflict",
        priority=55,
        condition=lambda ctx: (
            ctx.risk == "High"
            and ctx.glucose is not None
            and ctx.glucose < NORMAL_GLUCOSE_MAX
            and not ctx.fired_category("measurement")
        ),
        message=(
            "Mô hình dự đoán nguy cơ cao dù đường huyết đo được bình thường; một số đo bình thường không loại trừ nguy cơ, vì vậy giữ mức nguy cơ cao và khuyến nghị xét nghiệm A1C."
        ),
        basis="Nguyên tắc: không hạ nguy cơ mô hình chỉ vì một số đo đường huyết bình thường.",
        resolution="prediction_kept_confirm_with_a1c",
    ),
    Rule(
        code="CF-PRED-HIGH-LOW-QUALITY",
        name="Nguy cơ mô hình cao trên dữ liệu chất lượng thấp",
        category="conflict",
        priority=40,
        condition=lambda ctx: ctx.risk == "High" and ctx.confidence_label == "Low",
        message=(
            "Nguy cơ cao từ mô hình dựa trên dữ liệu đầu vào chất lượng thấp; coi là kết quả tạm thời và xác nhận bằng số đo thực tế."
        ),
        basis="Nguyên tắc: dự đoán trên đầu vào thiếu hoặc không hợp lý chỉ có tính tạm thời.",
        resolution="prediction_kept_marked_provisional",
    ),
    Rule(
        code="CF-ESCALATION-NO-EVIDENCE",
        name="Chuyển bác sĩ khi thiếu bằng chứng hướng dẫn",
        category="conflict",
        priority=30,
        condition=lambda ctx: (
            ctx.evidence_status in ("none", "limited")
            and ESCALATION_LEVELS.index(ctx.escalation) > 0
        ),
        message=(
            "Hướng xử trí do các luật trên quyết định trong khi bằng chứng hướng dẫn còn thiếu hoặc hạn chế; không hạ mức chuyển bác sĩ vì thiếu bằng chứng."
        ),
        basis="Nguyên tắc: hướng xử trí an toàn không phụ thuộc kết quả truy xuất.",
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
