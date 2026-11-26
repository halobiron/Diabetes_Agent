"""Nested CV on deduplicated UCI symptom profiles; never call this external validation.

Outer validation labels never select their own model, threshold or calibration.
Within every outer training partition, inner OOF predictions select the candidate
by AUC and a conservative recall target of .95. An outer failure is retained.
The earlier 51-profile holdout is already exposed; it is not reused as unseen test.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.mlp import TorchMLPClassifier
from models.screening import screening_threshold
from models.symptoms import SOURCE_URL, SYMPTOM_FEATURES, load_symptom_data


def score(y, p, pred):
    tn, fp, fn, tp = map(int, confusion_matrix(y, pred, labels=[0, 1]).ravel())
    return {
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn),
        "specificity": tn / (tn + fp),
        "accuracy": (tp + tn) / len(y),
        "f1": 2 * tp / (2 * tp + fp + fn),
        "roc_auc": float(roc_auc_score(y, p)),
        "average_precision": float(average_precision_score(y, p)),
        "confusion_matrix": {
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "true_positive": tp,
        },
    }


def interval(k, n):
    z = 1.959963984540054
    p = k / n
    d = 1 + z * z / n
    return [
        (p + z * z / (2 * n) - z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d,
        (p + z * z / (2 * n) + z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d,
    ]


def main():
    import torch

    torch.set_num_threads(4)
    folder = ROOT / "artifacts/symptom_nested_cv"
    folder.mkdir(exist_ok=True)
    data = ROOT / "data/train/symptoms/diabetes_data_upload.csv"
    X, y, raw_count = load_symptom_data(data)
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
    protocol = {
        "outer_folds": 5,
        "inner_folds": 3,
        "calibration": "sigmoid_cv3_inside_each_training_fold",
        "selection": "highest inner OOF AUC among candidates with precision >= .5 at recall target .95",
        "threshold_recall_target": 0.95,
        "seed": 42,
        "raw_rows": raw_count,
        "unique_rows": len(X),
        "deduplicate_before_split": True,
        "dataset_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "scope": "nested internal cross-validation; not external validation",
        "prior_failed_holdout": "artifacts/symptom_training/metrics.json",
        "candidate_names": list(candidates),
    }
    (folder / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    def select(Xt, yt):
        records = {}
        for name, base in candidates.items():
            model = CalibratedClassifierCV(clone(base), method="sigmoid", cv=3)
            p = cross_val_predict(
                model,
                Xt,
                yt,
                method="predict_proba",
                cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
                n_jobs=1,
            )[:, 1]
            threshold = screening_threshold(yt, p, 0.95)
            records[name] = {**score(yt, p, p >= threshold), "threshold": threshold}
        eligible = [n for n, r in records.items() if r["precision"] >= 0.5 and r["recall"] >= 0.95]
        if not eligible:
            raise RuntimeError("Inner training gate failed; keep production artifacts.")
        selected = max(eligible, key=lambda n: (records[n]["roc_auc"], records[n]["precision"]))
        model = CalibratedClassifierCV(clone(candidates[selected]), method="sigmoid", cv=3).fit(
            Xt, yt
        )
        return selected, records[selected]["threshold"], model, records

    probabilities = np.zeros(len(X))
    predictions = np.zeros(len(X), dtype=int)
    folds = []
    for number, (train_idx, eval_idx) in enumerate(
        StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y), 1
    ):
        name, t, model, search = select(X.iloc[train_idx], y.iloc[train_idx])
        p = model.predict_proba(X.iloc[eval_idx])[:, 1]
        probabilities[eval_idx] = p
        predictions[eval_idx] = p >= t
        fold = {
            "fold": number,
            "selected": name,
            "threshold": t,
            "inner_selection": search,
            "train_indices": train_idx.tolist(),
            "evaluation_indices": eval_idx.tolist(),
            "evaluation": score(y.iloc[eval_idx], p, p >= t),
        }
        folds.append(fold)
        (folder / "folds.json").write_text(json.dumps(folds, indent=2), encoding="utf-8")
        print("OUTER", number, name, json.dumps(fold["evaluation"]), flush=True)
    metrics = score(y, probabilities, predictions)
    cm = metrics["confusion_matrix"]
    ci = {
        "precision": interval(cm["true_positive"], cm["true_positive"] + cm["false_positive"]),
        "recall": interval(cm["true_positive"], cm["true_positive"] + cm["false_negative"]),
    }
    acceptance = {
        "precision_min": 0.5,
        "recall_min": 0.8,
        "specificity_min": 0.5,
        "passed": metrics["precision"] >= 0.5
        and metrics["recall"] >= 0.8
        and metrics["specificity"] >= 0.5,
    }
    report = {
        **protocol,
        "evaluation": metrics,
        "wilson_95_intervals": ci,
        "acceptance": acceptance,
        "always_positive": {"precision": float(y.mean()), "recall": 1.0, "specificity": 0.0},
        "folds": folds,
        "production_artifact_changed": False,
    }
    (folder / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.savez_compressed(
        folder / "outer_predictions.npz",
        labels=y.to_numpy(),
        probabilities=probabilities,
        predictions=predictions,
    )
    print("NESTED_RESULT", json.dumps(metrics), json.dumps(ci), flush=True)
    if not acceptance["passed"]:
        return 2
    # Final training uses exactly the same inner selection procedure on all unique profiles.
    name, t, model, search = select(X, y)
    meta = {
        **report,
        "selected_model": name,
        "model_version": f"symptoms-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        "task": "symptoms",
        "dataset_slug": "uci/early-stage-diabetes-risk-prediction",
        "selected_threshold": t,
        "risk_bands": {"low_max": t, "high_min": max(t + 0.1, 0.8)},
        "rows_total": len(X),
        "rows_raw": raw_count,
        "rows_train_final": len(X),
        "selection_method": protocol["selection"],
        "calibration": "sigmoid_cv3",
        "source": SOURCE_URL,
        "license": "CC BY 4.0",
        "doi": "10.24432/C5VG8H",
        "final_inner_selection": search,
        "feature_names": SYMPTOM_FEATURES,
        "scope": "Small, single-hospital Bangladesh dataset. Nested internal CV; no external/Vietnamese validation.",
        "metrics": {
            name: {
                "cv": {
                    "roc_auc_mean": float(np.mean([f["evaluation"]["roc_auc"] for f in folds])),
                    "roc_auc_std": float(np.std([f["evaluation"]["roc_auc"] for f in folds])),
                }
            }
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    artifact = {
        "model": model,
        "metadata": meta,
        "feature_names": SYMPTOM_FEATURES,
        "default_values": X.median().to_dict(),
        "training_frame": X.copy(),
    }
    joblib.dump(artifact, folder / "symptom_model.joblib")
    (folder / "metrics.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("SAVED", name, "threshold", t, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
