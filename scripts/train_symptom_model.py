"""Train a separate UCI-529 symptom model; deduplicate BEFORE splitting.

Validation selects model/threshold. Test is evaluated only after a frozen
decision is written. Preserves source prevalence; no resampling of evaluation.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.mlp import TorchMLPClassifier
from models.screening import ProbabilityEnsemble, screening_threshold
from models.symptoms import SOURCE_URL, SYMPTOM_FEATURES, load_symptom_data
from models.training_pipeline import evaluate_model, high_risk_cutoff


def main():
    import torch

    torch.set_num_threads(4)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standard-threshold",
        action="store_true",
        help="Use the user-approved RF threshold 0.5; explicitly label the holdout as reused.",
    )
    args = parser.parse_args()
    folder = ROOT / "artifacts/symptom_training"
    if args.standard_threshold:
        folder = folder / "standard_point"
    folder.mkdir(exist_ok=True, parents=True)
    path = ROOT / "data/train/symptoms/diabetes_data_upload.csv"
    X, y, raw_count = load_symptom_data(path)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )
    assert not set(map(tuple, X_train.to_numpy())) & set(map(tuple, X_test.to_numpy()))
    assert not set(map(tuple, X_val.to_numpy())) & set(map(tuple, X_test.to_numpy()))
    candidates = {
        "logistic": make_pipeline(
            StandardScaler(), LogisticRegression(C=1, max_iter=2000, random_state=42)
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, max_features=0.8, n_jobs=4, random_state=42
        ),
        "mlp": make_pipeline(
            StandardScaler(),
            TorchMLPClassifier(
                hidden_layers=(32, 16),
                positive_weight=1.0,
                epochs=250,
                patience=25,
                batch_size=32,
                learning_rate=0.003,
                dropout=0.1,
                weight_decay=0.001,
                random_state=42,
            ),
        ),
    }
    if args.standard_threshold:
        candidates = {"random_forest": candidates["random_forest"]}
    fitted = {}
    results = {}
    for name, estimator in candidates.items():
        cv = cross_val_score(
            estimator,
            X_train,
            y_train,
            scoring="roc_auc",
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
            n_jobs=1,
        )
        model = CalibratedClassifierCV(estimator, method="sigmoid", cv=3).fit(X_train, y_train)
        fitted[name] = model
        p = model.predict_proba(X_val)[:, 1]
        t = screening_threshold(y_val, p, 0.95)
        results[name] = {
            "cv_auc_mean": float(cv.mean()),
            "cv_auc_std": float(cv.std()),
            "threshold": t,
            "precision": float(precision_score(y_val, p >= t)),
            "recall": float(recall_score(y_val, p >= t)),
            "validation_auc": float(roc_auc_score(y_val, p)),
        }
        print(name, json.dumps(results[name]), flush=True)
    # A fixed equal-weight blend includes the required deep-learning component.
    if "mlp" in fitted:
        fitted["mlp_forest"] = ProbabilityEnsemble(
            [fitted["mlp"], fitted["random_forest"]], [0.5, 0.5]
        )
        p = fitted["mlp_forest"].predict_proba(X_val)[:, 1]
        t = screening_threshold(y_val, p, 0.95)
        results["mlp_forest"] = {
            "threshold": t,
            "precision": float(precision_score(y_val, p >= t)),
            "recall": float(recall_score(y_val, p >= t)),
            "validation_auc": float(roc_auc_score(y_val, p)),
        }
    eligible = [n for n, r in results.items() if r["precision"] >= 0.5 and r["recall"] >= 0.95]
    if not eligible:
        raise RuntimeError("No symptom candidate meets the validation gate.")
    # Retain DL when it meets the gate and is within one validation FP of best precision.
    best = max(eligible, key=lambda n: (results[n]["precision"], results[n]["validation_auc"]))
    dl = [
        n
        for n in ["mlp_forest", "mlp"]
        if n in eligible and results[n]["precision"] >= results[best]["precision"] - 0.03
    ]
    selected = (
        max(dl, key=lambda n: (results[n]["precision"], results[n]["validation_auc"]))
        if dl
        else best
    )
    model = fitted[selected]
    threshold = results[selected]["threshold"]
    if args.standard_threshold:
        selected = "random_forest"
        model = fitted[selected]
        threshold = 0.5
        validation_p = model.predict_proba(X_val)[:, 1]
        if (
            precision_score(y_val, validation_p >= threshold) < 0.5
            or recall_score(y_val, validation_p >= threshold) < 0.8
        ):
            raise RuntimeError("Standard RF threshold fails the validation requirements.")
    decision = {
        "selected": selected,
        "threshold": threshold,
        "validation_search": results,
        "split_seed": 42,
        "deduplicate_before_split": True,
        "raw_rows": raw_count,
        "unique_rows": len(X),
        "train_indices": X_train.index.tolist(),
        "validation_indices": X_val.index.tolist(),
        "test_indices": X_test.index.tolist(),
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "test_status": (
            "reused holdout after user-approved threshold review; not a new independent test"
            if args.standard_threshold
            else "initial holdout evaluation"
        ),
    }
    (folder / "frozen_selection.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    test = evaluate_model(model, X_test, y_test, threshold)
    validation = evaluate_model(model, X_val, y_val, threshold)
    acceptance = {
        "precision_min": 0.5,
        "recall_min": 0.8,
        "passed": test["precision"] >= 0.5 and test["recall"] >= 0.8,
    }
    positives = int(y_test.sum())
    n = len(y_test)
    from math import sqrt

    def proportion_confint(success, total):
        z = 1.959963984540054
        p = success / total
        center = (p + z * z / (2 * total)) / (1 + z * z / total)
        half = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
        return center - half, center + half

    cm = test["confusion_matrix"]
    intervals = {
        name: list(map(float, proportion_confint(success, total)))
        for name, success, total in [
            ("precision", cm["true_positive"], cm["true_positive"] + cm["false_positive"]),
            ("recall", cm["true_positive"], positives),
        ]
    }
    high = high_risk_cutoff(y_val, model.predict_proba(X_val)[:, 1], threshold, min_precision=0.9)
    report = {
        **decision,
        "source": SOURCE_URL,
        "license": "CC BY 4.0",
        "doi": "10.24432/C5VG8H",
        "selected_model": selected,
        "task": "symptoms",
        "dataset_slug": "uci/early-stage-diabetes-risk-prediction",
        "rows_total": len(X),
        "calibration": "sigmoid_cv3",
        "selection_method": "validation selected RF; standard 0.5 threshold approved after retrospective review"
        if args.standard_threshold
        else "validation selection",
        "model_version": f"symptoms-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        "selected_threshold": threshold,
        "risk_bands": {"low_max": threshold, "high_min": high},
        "feature_names": SYMPTOM_FEATURES,
        "rows_train": len(X_train),
        "rows_validation": len(X_val),
        "rows_test": n,
        "validation": validation,
        "test": test,
        "metrics": {selected: {"validation": validation, "test": test}},
        "acceptance": acceptance,
        "wilson_95_intervals": intervals,
        "always_positive_test": {"precision": positives / n, "recall": 1.0, "specificity": 0.0},
        "scope": "internal holdout from one small Bangladesh hospital dataset; not external or Vietnamese validation",
        "prevalence_warning": "precision depends on prevalence; these metrics are not BRFSS improvements",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (folder / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("FINAL", json.dumps(report), flush=True)
    if not acceptance["passed"]:
        return 2
    artifact = {
        "model": model,
        "metadata": report,
        "feature_names": SYMPTOM_FEATURES,
        "default_values": X_train.median().to_dict(),
        "training_frame": X_train.copy(),
    }
    joblib.dump(artifact, ROOT / "artifacts/symptom_model.joblib")
    (ROOT / "artifacts/symptom_metrics.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
