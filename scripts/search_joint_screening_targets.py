"""Second validation-only search for precision >= .5 and recall >= .8.

No test labels are read or scored. No production artifact is changed. Saves
every candidate result and rejects the run if the two targets are infeasible.
CatBoost is an optional experiment dependency (pip install catboost==1.2.10).
"""

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from models.mlp import TorchMLPClassifier
from models.screening import screening_threshold, select_screening_candidate
from models.training_pipeline import load_dataset_from_path


def main():
    import torch

    torch.set_num_threads(8)
    folder = ROOT / "artifacts" / "joint_target_search"
    folder.mkdir(exist_ok=True)
    path, X, y = load_dataset_from_path(ROOT / "data/train")
    # Preserve original split. Deliberately discard the historical test partition.
    X_dev, _, y_dev, _ = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=0.25, random_state=42, stratify=y_dev
    )
    X_fit, X_stop, y_fit, y_stop = train_test_split(
        X_train, y_train, test_size=0.1, random_state=73, stratify=y_train
    )
    baseline = joblib.load(ROOT / "artifacts/screening_optimization/baseline/risk_model.joblib")
    results, predictions = {}, {}
    config = {
        "minimum_precision": 0.5,
        "minimum_recall": 0.8,
        "selection_partition": "original validation, seed42; test never evaluated in this search",
        "rows_train": len(X_train),
        "rows_fit_boosting": len(X_fit),
        "rows_early_stopping": len(X_stop),
        "rows_validation": len(X_val),
        "validation_positive": int(y_val.sum()),
        "features": list(X.columns),
        "excluded": ["ID"],
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "catboost_version": __import__("catboost").__version__,
    }
    (folder / "protocol.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    def record(name, p, model=None, **details):
        threshold = screening_threshold(y_val, p, 0.8)
        flagged = p >= threshold
        tp = int(((y_val.to_numpy() == 1) & flagged).sum())
        fp = int(((y_val.to_numpy() == 0) & flagged).sum())
        precision, recall, thresholds = precision_recall_curve(y_val, p)
        at50 = np.flatnonzero(precision[:-1] >= 0.5)
        max_recall = float(recall[at50].max()) if len(at50) else 0.0
        result = {
            "threshold_at_recall80": threshold,
            "precision": tp / (tp + fp),
            "recall": tp / int(y_val.sum()),
            "average_precision": float(average_precision_score(y_val, p)),
            "roc_auc": float(roc_auc_score(y_val, p)),
            "max_recall_at_precision50": max_recall,
            **details,
        }
        result["meets_both"] = result["precision"] >= 0.5 and result["recall"] >= 0.8
        results[name] = result
        predictions[name] = np.asarray(p)
        print(name, json.dumps(result), flush=True)
        (folder / "validation_results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        # Only save trained weights if there is a candidate worth calibrating further.
        if result["meets_both"] and model is not None:
            joblib.dump(model, folder / f"{name}.joblib")

    record("baseline_mlp", baseline["model"].predict_proba(X_val)[:, 1])
    current = joblib.load(ROOT / "artifacts/risk_model.joblib")
    record("current_ensemble", current["model"].predict_proba(X_val)[:, 1])
    # Raw scores retain ordering and avoid isotonic score plateaus.
    for leaves, reg, weight in [(7, 5, 1), (15, 10, 1), (31, 20, 1), (15, 10, 3), (31, 20, 6)]:
        started = time.perf_counter()
        model = LGBMClassifier(
            n_estimators=2400,
            learning_rate=0.025,
            num_leaves=leaves,
            reg_lambda=reg,
            min_child_samples=80,
            colsample_bytree=0.95,
            scale_pos_weight=weight,
            metric="average_precision",
            random_state=42,
            n_jobs=8,
            verbosity=-1,
        )
        model.fit(
            X_fit,
            y_fit,
            eval_set=[(X_stop, y_stop)],
            callbacks=[
                early_stopping(120, first_metric_only=True, verbose=False),
                log_evaluation(0),
            ],
        )
        record(
            f"lgbm_raw_leaves{leaves}_l2{reg}_weight{weight}",
            model.predict_proba(X_val)[:, 1],
            model,
            seconds=time.perf_counter() - started,
            iterations=model.best_iteration_,
        )

    for depth, reg, weight in [(4, 5, 1), (6, 5, 1), (8, 10, 1), (6, 10, 3)]:
        started = time.perf_counter()
        model = CatBoostClassifier(
            iterations=1800,
            depth=depth,
            learning_rate=0.035,
            l2_leaf_reg=reg,
            class_weights=[1, weight],
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=42,
            task_type="GPU" if torch.cuda.is_available() else "CPU",
            thread_count=8,
            allow_writing_files=False,
            verbose=False,
        )
        model.fit(X_fit, y_fit, eval_set=(X_stop, y_stop), early_stopping_rounds=120, verbose=False)
        record(
            f"catboost_numeric_depth{depth}_l2{reg}_weight{weight}",
            model.predict_proba(X_val)[:, 1],
            model,
            seconds=time.perf_counter() - started,
            iterations=model.tree_count_,
        )

    for leaves, reg in [(15, 5), (31, 10)]:
        started = time.perf_counter()
        model = HistGradientBoostingClassifier(
            max_iter=600,
            learning_rate=0.035,
            max_leaf_nodes=leaves,
            l2_regularization=reg,
            min_samples_leaf=80,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=30,
            random_state=42,
        )
        with threadpool_limits(limits=8):
            model.fit(X_train, y_train)
            p = model.predict_proba(X_val)[:, 1]
        record(f"histgb_leaves{leaves}_l2{reg}", p, model, seconds=time.perf_counter() - started)

    categorical = [c for c in X.columns if c not in ["BMI", "MentHlth", "PhysHlth"]]
    for weight, encoded in [(1.0, False), (3.0, False), (1.0, True)]:
        started = time.perf_counter()
        transformer = (
            ColumnTransformer(
                [
                    (
                        "categorical",
                        OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        categorical,
                    ),
                    ("numeric", StandardScaler(), ["BMI", "MentHlth", "PhysHlth"]),
                ]
            )
            if encoded
            else StandardScaler()
        )
        model = Pipeline(
            [
                ("features", transformer),
                (
                    "mlp",
                    TorchMLPClassifier(
                        hidden_layers=(128, 64),
                        positive_weight=weight,
                        epochs=70,
                        patience=10,
                        batch_size=2048,
                        dropout=0.2,
                        learning_rate=0.0007,
                        weight_decay=0.001,
                        random_state=52,
                    ),
                ),
            ]
        )
        with threadpool_limits(limits=8):
            model.fit(X_train, y_train)
            p = model.predict_proba(X_val)[:, 1]
        record(
            f"mlp_weight{weight}_onehot{int(encoded)}",
            p,
            model,
            seconds=time.perf_counter() - started,
        )

    # Fixed, equal-rank ensembles; weights not fitted using validation labels.
    base_names = list(predictions)
    ranks = {n: __import__("scipy").stats.rankdata(predictions[n]) / len(X_val) for n in base_names}
    for prefix in ["lgbm_raw", "catboost_", "mlp_weight", "histgb_"]:
        members = [n for n in base_names if n.startswith(prefix)]
        if members:
            record(
                f"rank_average_{prefix}",
                np.mean([ranks[n] for n in members], axis=0),
                members=members,
            )
    members = [n for n in base_names if n not in ["baseline_mlp", "current_ensemble"]]
    record("rank_average_all_new", np.mean([ranks[n] for n in members], axis=0), members=members)
    try:
        selected = select_screening_candidate(results, 0.8, 0.5)
        status = "validation_targets_met_needs_independent_confirmation"
    except ValueError:
        selected = None
        status = "targets_not_met"
    summary = {
        **config,
        "status": status,
        "selected_candidate": selected,
        "candidates": len(results),
        "feasible": sum(r["meets_both"] for r in results.values()),
        "best_precision_at_recall80": max(results, key=lambda n: results[n]["precision"]),
        "best_recall_at_precision50": max(
            results, key=lambda n: results[n]["max_recall_at_precision50"]
        ),
        "production_artifact_changed": False,
    }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    np.savez_compressed(
        folder / "validation_predictions.npz", labels=y_val.to_numpy(), **predictions
    )
    print("FINAL", json.dumps(summary), flush=True)
    return 0 if selected else 2


if __name__ == "__main__":
    raise SystemExit(main())
