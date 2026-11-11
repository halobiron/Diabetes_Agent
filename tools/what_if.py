"""Counterfactual queries against the risk model.

Two uses of the same idea (change a model input, re-score):
- `scenarios`: what the estimate would be if the patient changed one modifiable factor.
- `most_informative_unknown`: which input the patient left out would move the estimate most.

Both are statistical associations learned from survey data, not proof that a change
causes the same drop in one person's risk.
"""

from dataclasses import dataclass
from typing import Callable

from models.risk_model import RiskModel
from tools.risk_classifier import classify_risk

MIN_CHANGE = 0.001  # smaller than 0.1 percentage points is noise, not a scenario
MIN_SWING = 0.02  # an unknown input must be able to move the estimate by 2 points to be asked
WEIGHT_LOSS_FRACTION = 0.05  # giảm từ 5% cân nặng trở lên (Vinmec, WHO)

# Yes/no inputs a patient can reasonably be asked about, by model feature.
ASKABLE_FEATURES = (
    "PhysActivity",
    "Smoker",
    "HighChol",
    "HeartDiseaseorAttack",
    "Stroke",
    "DiffWalk",
    "HvyAlcoholConsump",
    "Fruits",
    "Veggies",
)
# Request keys for the same inputs (the API's `skipped_fields` uses these).
ASKABLE_FIELDS = tuple(RiskModel.FEATURE_KEYS[feature] for feature in ASKABLE_FEATURES)


@dataclass(frozen=True)
class Scenario:
    key: str
    label: Callable[[dict], str]
    evidence_ids: tuple
    applies: Callable[[dict, "WhatIfSimulator"], bool]
    apply: Callable[[dict], None]  # edits a {feature: value} row in place


def _supplied_equals(feature, value):
    """True when the model uses `feature`, the patient gave it, and it currently equals `value`."""

    def check(patient, simulator):
        key = simulator.model.FEATURE_KEYS[feature]
        return (
            feature in simulator.model.feature_names
            and feature not in patient.get("defaulted_fields", [])
            and patient.get(key) == value
        )

    return check


def _lose_weight(row):
    for name in ("BMI", "bmi"):
        if name in row:
            row[name] *= 1 - WEIGHT_LOSS_FRACTION


def _set(feature, value):
    def apply(row):
        if feature in row:
            row[feature] = value

    return apply


def _lower_bp(row):
    _set("HighBP", 0)(row)
    if "bp" in row:
        row["bp"] = min(row["bp"], 139)


def _weight_label(patient):
    weight = patient.get("weight_kg")
    kilos = f" (khoảng {weight * WEIGHT_LOSS_FRACTION:.1f} kg)" if weight else ""
    return f"Giảm {WEIGHT_LOSS_FRACTION:.0%} cân nặng{kilos}"


SCENARIOS = (
    Scenario(
        "weight_loss",
        _weight_label,
        ("ev-vinmec-chan-doan-dieu-tri-cf7a80ca", "ev-vinmec-tien-dtd-tien-trien-799a8df9"),
        lambda patient, sim: patient["bmi"] >= 25
        and any(name in sim.model.feature_names for name in ("BMI", "bmi")),
        _lose_weight,
    ),
    Scenario(
        "physical_activity",
        lambda patient: "Vận động thể chất đều đặn (khoảng 150 phút mỗi tuần)",
        ("ev-who-diabetes-6dcdf201", "ev-vinmec-tien-dtd-tien-trien-799a8df9"),
        _supplied_equals("PhysActivity", 0),
        _set("PhysActivity", 1),
    ),
    Scenario(
        "smoking_cessation",
        lambda patient: "Bỏ thuốc lá",
        ("ev-vinmec-tien-dtd-an-gi-ea43d279", "ev-vinmec-tien-dtd-tien-trien-799a8df9"),
        _supplied_equals("Smoker", 1),
        _set("Smoker", 0),
    ),
    Scenario(
        "blood_pressure",
        lambda patient: "Đưa huyết áp tâm thu xuống dưới 140 mmHg (mục tiêu của Bộ Y tế)",
        ("ev-moh-qt-2017-abf7bd04",),
        lambda patient, sim: patient.get("high_bp") == 1
        and any(name in sim.model.feature_names for name in ("HighBP", "bp")),
        _lower_bp,
    ),
)


class WhatIfSimulator:
    def __init__(self, risk_model):
        self.model = risk_model

    def _score(self, base_row, changes):
        row = {**base_row}
        for change in changes:
            change(row)
        return self.model.probability(self.model.row_frame(row))

    def _entry(self, key, label, evidence_ids, before, after):
        return {
            "key": key,
            "label": label,
            "probability_after": after,
            "change": after - before,
            "risk_after": classify_risk(after, self.model.risk_bands),
            "evidence_ids": list(evidence_ids),
        }

    def scenarios(self, patient):
        """Re-score the patient under each applicable modifiable-factor change, plus all combined."""
        base = self.model.feature_frame(patient).iloc[0].to_dict()
        before = self.model.probability(self.model.row_frame(base))
        applicable = [s for s in SCENARIOS if s.applies(patient, self)]

        entries = []
        for scenario in applicable:
            after = self._score(base, [scenario.apply])
            if before - after >= MIN_CHANGE:
                entries.append(
                    self._entry(
                        scenario.key, scenario.label(patient), scenario.evidence_ids, before, after
                    )
                )
        entries.sort(key=lambda entry: entry["change"])

        combined = None
        if len(entries) > 1:
            kept = {entry["key"] for entry in entries}
            after = self._score(base, [s.apply for s in applicable if s.key in kept])
            evidence_ids = dict.fromkeys(i for e in entries for i in e["evidence_ids"])
            combined = self._entry(
                "combined", "Thực hiện đồng thời các thay đổi trên", evidence_ids, before, after
            )
        return {"probability_before": before, "scenarios": entries, "combined": combined}

    def most_informative_unknown(self, patient):
        """The yes/no input the patient left out whose answer could move the estimate most."""
        skipped = set(patient.get("skipped_fields", []))
        base = self.model.feature_frame(patient).iloc[0].to_dict()
        best = None
        for feature in ASKABLE_FEATURES:
            field = self.model.FEATURE_KEYS[feature]
            if (
                feature not in patient.get("defaulted_fields", [])
                or field in skipped
                or feature not in base
            ):
                continue
            if_no = self._score(base, [_set(feature, 0)])
            if_yes = self._score(base, [_set(feature, 1)])
            swing = abs(if_yes - if_no)
            if swing >= MIN_SWING and (best is None or swing > best["swing"]):
                best = {
                    "feature": feature,
                    "field": field,
                    "probability_if_no": if_no,
                    "probability_if_yes": if_yes,
                    "swing": swing,
                }
        return best
