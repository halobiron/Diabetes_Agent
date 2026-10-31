"""Local training pipeline: CV model selection, tuning, calibration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

try:
    from lightgbm import LGBMClassifier

    HAS_LIGHTGBM = True
except Exception:
    HAS_LIGHTGBM = False

FEATURE_NAMES = [
    "HighBP",
    "HighChol",
    "CholCheck",
    "BMI",
    "Smoker",
    "Stroke",
    "HeartDiseaseorAttack",
    "PhysActivity",
    "Fruits",
    "Veggies",
    "HvyAlcoholConsump",
    "AnyHealthcare",
    "NoDocbcCost",
    "GenHlth",
    "MentHlth",
    "PhysHlth",
    "DiffWalk",
    "Sex",
    "Age",
    "Education",
    "Income",
]
DATASET_SLUG = "alexteboul/diabetes-health-indicators-dataset"
PREFERRED_CSV_NAMES = [
    "diabetes_binary_health_indicators_BRFSS2015.csv",
    "diabetes_binary_5050split_health_indicators_BRFSS2015.csv",
]
TARGET_COLUMN = "Diabetes_binary"
RANDOM_STATE = 42
CV_FOLDS = 5
TUNE_ITERATIONS = 12
TOP_K_TO_TUNE = 2


def resolve_data_path(path):
    data_path = Path(path)
    if data_path.is_file():
        return data_path

    candidates = [data_path / name for name in PREFERRED_CSV_NAMES]
    candidates.extend(sorted(data_path.glob("*.csv")))
    for candidate in candidates:
        if candidate.is_file() and TARGET_COLUMN in pd.read_csv(candidate, nrows=0).columns:
            return candidate

    raise FileNotFoundError(
        f"No CSV with '{TARGET_COLUMN}' for binary training found at {data_path}"
    )


def load_dataset_from_path(path):
    data_path = resolve_data_path(path)
    df = pd.read_csv(data_path)
    missing = [column for column in [TARGET_COLUMN, *FEATURE_NAMES] if column not in df]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if not df[TARGET_COLUMN].isin([0, 1]).all():
        raise ValueError(f"'{TARGET_COLUMN}' must contain only 0/1 for binary training.")
    return data_path, df[FEATURE_NAMES].copy(), df[TARGET_COLUMN].astype(int)


def class_sample_weight(y):
    classes = np.array(sorted(y.unique()))
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    lookup = dict(zip(classes, weights))
    return y.map(lookup).to_numpy()


def uses_sample_weight(model_name):
    return model_name in {"hist_gradient_boosting", "random_forest", "lightgbm"}


def candidate_models():
    models = {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            early_stopping=True,
            l2_regularization=0.1,
            learning_rate=0.05,
            max_iter=300,
            random_state=RANDOM_STATE,
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced_subsample",
            max_depth=14,
            min_samples_leaf=8,
            n_estimators=180,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
    }
    if HAS_LIGHTGBM:
        models["lightgbm"] = LGBMClassifier(
            class_weight="balanced",
            learning_rate=0.05,
            n_estimators=300,
            num_leaves=31,
            random_state=RANDOM_STATE,
            verbose=-1,
        )
    return models


def tuning_grids():
    return {
        "hist_gradient_boosting": {
            "learning_rate": [0.03, 0.05, 0.08],
            "max_iter": [250, 350, 450],
            "max_depth": [None, 8, 12],
            "min_samples_leaf": [10, 20, 40],
            "l2_regularization": [0.0, 0.1, 0.5],
        },
        "lightgbm": {
            "learning_rate": [0.03, 0.05, 0.08],
            "n_estimators": [200, 300, 400],
            "num_leaves": [31, 63, 95],
            "min_child_samples": [20, 40, 80],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
        },
    }


def fit_estimator(name, model, X_train, y_train, sample_weight):
    if uses_sample_weight(name):
        model.fit(X_train, y_train, sample_weight=sample_weight)
    else:
        model.fit(X_train, y_train)
    return model


def cross_val_roc_auc(name, model, X, y, sample_weight):
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = []
    for train_idx, val_idx in cv.split(X, y):
        estimator = clone(model)
        sw = sample_weight[train_idx] if sample_weight is not None else None
        fit_estimator(
            name,
            estimator,
            X.iloc[train_idx],
            y.iloc[train_idx],
            sw,
        )
        y_prob = estimator.predict_proba(X.iloc[val_idx])[:, 1]
        scores.append(roc_auc_score(y.iloc[val_idx], y_prob))
    return {
        "cv_roc_auc_mean": round(float(np.mean(scores)), 5),
        "cv_roc_auc_std": round(float(np.std(scores)), 5),
    }


def tune_model(name, model, X_train, y_train, sample_weight):
    grid = tuning_grids().get(name)
    if not grid:
        return model, {}

    search = RandomizedSearchCV(
        model,
        param_distributions=grid,
        n_iter=TUNE_ITERATIONS,
        scoring="roc_auc",
        cv=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0,
    )
    if uses_sample_weight(name):
        search.fit(X_train, y_train, sample_weight=sample_weight)
    else:
        search.fit(X_train, y_train)
    return search.best_estimator_, {
        "best_params": search.best_params_,
        "cv_roc_auc_tune": round(float(search.best_score_), 5),
    }


def calibrate_model(model, X_train, y_train):
    calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train)
    return calibrated


def best_f1_threshold(y_true, y_prob):
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    if len(thresholds) == 0:
        return 0.5

    precision = precision[:-1]
    recall = recall[:-1]
    denominator = precision + recall
    f1_scores = np.divide(
        2 * precision * recall,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator != 0,
    )
    return thresholds[int(np.argmax(f1_scores))]


def evaluate_model(model, X_test, y_test):
    y_prob = model.predict_proba(X_test)[:, 1]
    default_pred = (y_prob >= 0.5).astype(int)
    threshold = best_f1_threshold(y_test, y_prob)
    tuned_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, tuned_pred).ravel()
    return {
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 5),
        "average_precision": round(float(average_precision_score(y_test, y_prob)), 5),
        "brier_score": round(float(brier_score_loss(y_test, y_prob)), 5),
        "accuracy_at_0_5": round(float(accuracy_score(y_test, default_pred)), 5),
        "precision_at_0_5": round(float(precision_score(y_test, default_pred, zero_division=0)), 5),
        "recall_at_0_5": round(float(recall_score(y_test, default_pred, zero_division=0)), 5),
        "f1_at_0_5": round(float(f1_score(y_test, default_pred, zero_division=0)), 5),
        "selected_threshold": round(float(threshold), 5),
        "accuracy": round(float(accuracy_score(y_test, tuned_pred)), 5),
        "precision": round(float(precision_score(y_test, tuned_pred, zero_division=0)), 5),
        "recall": round(float(recall_score(y_test, tuned_pred, zero_division=0)), 5),
        "f1": round(float(f1_score(y_test, tuned_pred, zero_division=0)), 5),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }


def rank_models(cv_results):
    return sorted(
        cv_results.items(),
        key=lambda item: (item[1]["cv_roc_auc_mean"], -item[1]["cv_roc_auc_std"]),
        reverse=True,
    )


def train_production_model(X, y, data_path, output_dir, explanation_sample_size=2500):
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    sample_weight = class_sample_weight(y_train)
    base_models = candidate_models()

    cv_results = {}
    for name, model in base_models.items():
        cv_results[name] = cross_val_roc_auc(name, model, X_train, y_train, sample_weight)
        print(f"CV {name}: {cv_results[name]}")

    ranked = rank_models(cv_results)
    tune_targets = {name for name, _ in ranked[:TOP_K_TO_TUNE]}

    final_models = {}
    tuning_metadata = {}
    test_metrics = {}

    for name, model in base_models.items():
        estimator = clone(model)
        if name in tune_targets:
            estimator, tuning_metadata[name] = tune_model(
                name, estimator, X_train, y_train, sample_weight
            )
        else:
            fit_estimator(name, estimator, X_train, y_train, sample_weight)

        calibrated = calibrate_model(estimator, X_train, y_train)
        final_models[name] = calibrated
        test_metrics[name] = {
            **cv_results[name],
            **(tuning_metadata.get(name) or {}),
            **evaluate_model(calibrated, X_test, y_test),
        }

    selected_name = max(
        test_metrics.items(),
        key=lambda item: (item[1]["roc_auc"], item[1]["f1"]),
    )[0]

    metadata = {
        "schema_version": 2,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_slug": DATASET_SLUG,
        "dataset_path": str(data_path),
        "target": TARGET_COLUMN,
        "rows_total": int(len(X)),
        "rows_train": int(len(X_train)),
        "rows_test": int(len(X_test)),
        "feature_names": FEATURE_NAMES,
        "selected_model": selected_name,
        "selection_method": f"{CV_FOLDS}-fold_cv_then_holdout_test",
        "calibration": "isotonic_cv3",
        "tuned_models": sorted(tune_targets),
        "lightgbm_available": HAS_LIGHTGBM,
        "metrics": test_metrics,
        "sklearn_version": sklearn.__version__,
    }

    training_frame = X_train.sample(
        n=min(explanation_sample_size, len(X_train)),
        random_state=RANDOM_STATE,
    )
    artifact = {
        "schema_version": 2,
        "model": final_models[selected_name],
        "feature_names": FEATURE_NAMES,
        "default_values": X_train.median(numeric_only=True).to_dict(),
        "default_glucose": 100.0,
        "training_frame": training_frame,
        "metadata": metadata,
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_dir / "risk_model.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_model_card(output_dir / "model_card.md", metadata)

    print(f"Selected model: {selected_name}")
    print(json.dumps(test_metrics[selected_name], indent=2))
    print(f"Saved outputs under {output_dir}")
    return metadata


def write_model_card(path, metadata):
    metrics = metadata["metrics"][metadata["selected_model"]]
    path.write_text(
        f"""# Healthcare Diabetes Risk Model Card

## Intended Use

This model estimates diabetes risk from CDC BRFSS health indicators for an educational
healthcare AI prototype. It is not a diagnostic medical device.

## Dataset

- Source: Kaggle `{DATASET_SLUG}`
- Target: `{TARGET_COLUMN}`
- Rows: {metadata["rows_total"]}
- Features: {len(metadata["feature_names"])}

## Training

- Selection: {metadata["selection_method"]}
- Hyperparameter tuning: {", ".join(metadata["tuned_models"]) or "none"}
- Probability calibration: {metadata["calibration"]}
- LightGBM included: {metadata["lightgbm_available"]}

## Selected Model

- Model: `{metadata["selected_model"]}`
- CV ROC AUC: {metrics["cv_roc_auc_mean"]} (+/- {metrics["cv_roc_auc_std"]})
- Holdout ROC AUC: {metrics["roc_auc"]}
- Average precision: {metrics["average_precision"]}
- Brier score: {metrics["brier_score"]}
- Tuned F1: {metrics["f1"]}
- Tuned threshold: {metrics["selected_threshold"]}
""",
        encoding="utf-8",
    )
