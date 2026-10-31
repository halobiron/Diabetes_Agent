import pandas as pd
from joblib import dump
from sklearn.linear_model import LogisticRegression

from models.risk_model import RiskModel


def _training_df():
    return pd.DataFrame(
        [
            {"age": 30, "height_cm": 175, "weight_kg": 70, "bp": 118, "glucose": 90, "target": 0},
            {"age": 62, "height_cm": 165, "weight_kg": 88, "bp": 160, "glucose": 220, "target": 1},
            {"age": 48, "height_cm": 170, "weight_kg": 82, "bp": 138, "glucose": 150, "target": 1},
            {"age": 34, "height_cm": 180, "weight_kg": 72, "bp": 122, "glucose": 95, "target": 0},
        ]
    )


def test_calculate_bmi():
    bmi = RiskModel.calculate_bmi(175, 70)
    assert round(bmi, 1) == 22.9


def test_assess_with_missing_glucose_uses_default():
    model = RiskModel()
    model.train(_training_df())
    prob, patient = model.assess(
        {"age": 45, "height_cm": 172, "weight_kg": 80, "bp": 130, "glucose": None}
    )
    assert 0 <= prob <= 1
    assert patient["glucose_measured"] is False
    assert patient["glucose"] == model.default_glucose


def test_assess_with_bmi_and_null_height_weight():
    model = RiskModel()
    model.train(_training_df())

    prob, patient = model.assess(
        {"age": 52, "bp": 140, "bmi": 30, "height_cm": None, "weight_kg": None}
    )

    assert 0 <= prob <= 1
    assert patient["bmi"] == 30
    assert patient["height_cm"] is None
    assert patient["weight_kg"] is None


def test_load_brfss_artifact_derives_features(tmp_path):
    rows = [
        {feature: 0 for feature in RiskModel.BRFSS_FEATURE_NAMES},
        {feature: 1 for feature in RiskModel.BRFSS_FEATURE_NAMES},
        {feature: 0 for feature in RiskModel.BRFSS_FEATURE_NAMES},
        {feature: 1 for feature in RiskModel.BRFSS_FEATURE_NAMES},
    ]
    df = pd.DataFrame(rows)
    df["BMI"] = [23, 35, 26, 41]
    df["Age"] = [3, 9, 4, 12]
    df["GenHlth"] = [1, 4, 2, 5]
    df["Education"] = [6, 3, 5, 2]
    df["Income"] = [8, 4, 7, 2]
    target = [0, 1, 0, 1]

    fitted = LogisticRegression(max_iter=1000).fit(df, target)
    artifact_path = tmp_path / "risk_model.joblib"
    dump(
        {
            "model": fitted,
            "feature_names": RiskModel.BRFSS_FEATURE_NAMES,
            "default_values": df.median(numeric_only=True).to_dict(),
            "default_glucose": 100.0,
            "training_frame": df,
            "metadata": {"selected_model": "test_logistic_regression"},
        },
        artifact_path,
    )

    model = RiskModel().load_artifact(artifact_path)
    prob, patient = model.assess(
        {
            "age": 52,
            "height_cm": 170,
            "weight_kg": 88,
            "bp": 142,
            "sex": "male",
            "high_chol": True,
            "general_health": 4,
        }
    )

    assert 0 <= prob <= 1
    assert patient["high_bp"] == 1
    assert patient["age_bucket"] == 7
    assert patient["sex"] == 1
    assert model.artifact_metadata["selected_model"] == "test_logistic_regression"
