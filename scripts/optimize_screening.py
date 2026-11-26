"""Optimize ranking and a recall-constrained operating point on validation only.

The historical test split has already been reported. It is reused for a paired
comparison, not represented as a new independent external validation set.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from models.screening import ProbabilityEnsemble, screening_threshold, select_screening_candidate
from models.training_pipeline import (
    RANDOM_STATE,
    TEST_SIZE,
    VALIDATION_SIZE,
    best_f1_threshold,
    evaluate_model,
    high_risk_cutoff,
    load_dataset_from_path,
    write_model_card,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimum-recall", type=float, default=0.8)
    parser.add_argument("--minimum-precision", type=float, default=0.5)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    if not 0 < args.minimum_recall <= 1:
        parser.error("--minimum-recall must be in (0, 1].")
    if not 0 < args.minimum_precision <= 1:
        parser.error("--minimum-precision must be in (0, 1].")
    folder = ROOT / "artifacts" / "screening_optimization"
    folder.mkdir(exist_ok=True)
    baseline = folder / "baseline"
    if not baseline.exists():
        baseline.mkdir()
        for name in ["risk_model.joblib", "metrics.json", "model_card.md"]:
            shutil.copy2(ROOT / "artifacts" / name, baseline / name)
    old = joblib.load(baseline / "risk_model.joblib")
    old_meta = json.loads((baseline / "metrics.json").read_text(encoding="utf-8"))
    data_path, X, y = load_dataset_from_path(ROOT / "data" / "train")
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev, y_dev, test_size=VALIDATION_SIZE, random_state=RANDOM_STATE, stratify=y_dev
    )
    X_fit, X_cal, y_fit, y_cal = train_test_split(
        X_train, y_train, test_size=0.2, random_state=73, stratify=y_train
    )
    # Calibration and early stopping both stay inside the original training split.
    candidates = {"baseline_mlp": old["model"]}
    results = {}
    probabilities = {}

    def record(name, model):
        p = model.predict_proba(X_val)[:, 1]
        threshold = screening_threshold(y_val, p, args.minimum_recall)
        pred = p >= threshold
        result = dict(
            threshold=threshold,
            precision=float(precision_score(y_val, pred)),
            recall=float(recall_score(y_val, pred)),
            average_precision=float(average_precision_score(y_val, p)),
            roc_auc=float(roc_auc_score(y_val, p)),
        )
        candidates[name] = model
        probabilities[name] = p
        results[name] = result
        print(name, json.dumps(result), flush=True)
        (folder / "validation_search.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )

    record("baseline_mlp", old["model"])
    # Fixed small search: depth/regularization and unweighted vs balanced loss.
    for leaves, reg, balanced in [
        (7, 5, False),
        (15, 5, False),
        (31, 5, False),
        (15, 20, False),
        (31, 20, False),
        (15, 5, True),
    ]:
        name = f"lgbm_leaves{leaves}_l2_{reg}_balanced{int(balanced)}"
        estimator = LGBMClassifier(
            n_estimators=1800,
            learning_rate=0.025,
            num_leaves=leaves,
            reg_lambda=reg,
            min_child_samples=100,
            colsample_bytree=0.9,
            class_weight="balanced" if balanced else None,
            random_state=42,
            n_jobs=8,
            verbosity=-1,
        )
        estimator.fit(
            X_fit,
            y_fit,
            eval_set=[(X_cal, y_cal)],
            eval_metric="average_precision",
            callbacks=[
                early_stopping(100, first_metric_only=True, verbose=False),
                log_evaluation(0),
            ],
        )
        model = CalibratedClassifierCV(FrozenEstimator(estimator), method="isotonic").fit(
            X_cal, y_cal
        )
        record(name, model)
        joblib.dump(model, folder / f"{name}.joblib")
    # Weights fixed in advance; every blend retains the deep-learning component.
    for name in list(candidates):
        if name == "baseline_mlp":
            continue
        for weight in [0.25, 0.5, 0.75]:
            blend = ProbabilityEnsemble([old["model"], candidates[name]], [weight, 1 - weight])
            record(f"blend_mlp{weight}_{name}", blend)

    try:
        selected = select_screening_candidate(results, args.minimum_recall, args.minimum_precision)
    except ValueError as exc:
        rejection = {
            "status": "targets_not_met",
            "minimum_recall": args.minimum_recall,
            "minimum_precision": args.minimum_precision,
            "validation_results": results,
            "production_artifacts_changed": False,
        }
        (folder / "rejected_search.json").write_text(
            json.dumps(rejection, indent=2), encoding="utf-8"
        )
        print(str(exc), flush=True)
        return 2
    model = candidates[selected]
    threshold = results[selected]["threshold"]
    # Freeze the complete selection BEFORE looking at the reused test split.
    decision = dict(
        selected_model=selected,
        selected_threshold=threshold,
        minimum_validation_recall=args.minimum_recall,
        minimum_validation_precision=args.minimum_precision,
        selection="maximum validation precision subject to recall target; AP then AUC tie-break",
        validation_results=results,
        test_status="historical holdout reused for paired comparison; not external validation",
    )
    (folder / "frozen_selection.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    metrics = {
        name: evaluate_model(m, X_test, y_test, threshold=t)
        for name, m, t in [
            ("baseline_original", old["model"], old_meta["selected_threshold"]),
            ("baseline_recall_target", old["model"], results["baseline_mlp"]["threshold"]),
            ("optimized", model, threshold),
        ]
    }
    selected_val = evaluate_model(model, X_val, y_val, threshold=threshold)
    # Include max-F1 to separate ranking improvements from the recall/precision tradeoff.
    f1_threshold = float(best_f1_threshold(y_val, probabilities[selected]))
    metrics["optimized_validation_f1_threshold"] = evaluate_model(
        model, X_test, y_test, f1_threshold
    )
    report = {
        **decision,
        "test_comparisons": metrics,
        "validation_selected": selected_val,
        "validation_f1_threshold": f1_threshold,
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "rows_fit": len(X_fit),
        "rows_calibration": len(X_cal),
        "historical_model_version": old_meta["model_version"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (folder / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    high = high_risk_cutoff(y_val, probabilities[selected], threshold)
    meta = {
        **old_meta,
        "model_version": f"screening-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        "selected_model": selected,
        "selected_threshold": threshold,
        "risk_bands": {
            "low_max": threshold,
            "high_min": high,
            "high_min_rule": "lowest validation probability with precision >= 0.5",
        },
        "selection_method": decision["selection"],
        "minimum_validation_recall": args.minimum_recall,
        "historical_tuned_models": old_meta["tuned_models"],
        "tuned_models": ["lightgbm_six_configurations", "mlp_blend_weights"],
        "optimization": report,
        "calibration": "baseline isotonic_cv3; new LightGBM isotonic on internal training calibration split",
        "trained_at": report["created_at"],
    }
    meta["metrics"] = {
        **old_meta["metrics"],
        selected: {"validation": selected_val, "test": metrics["optimized"]},
    }
    artifact = {**old, "model": model, "metadata": meta}
    joblib.dump(artifact, folder / "risk_model.joblib")
    (folder / "metrics.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_model_card(folder / "model_card.md", meta)
    # Guard promotion: validation benefit beyond simply lowering the MLP threshold.
    promote = (
        results[selected]["precision"] >= results["baseline_mlp"]["precision"]
        and results[selected]["average_precision"] >= results["baseline_mlp"]["average_precision"]
    )
    if args.promote and promote:
        for name in ["risk_model.joblib", "metrics.json", "model_card.md"]:
            shutil.copy2(folder / name, ROOT / "artifacts" / name)
        print("PROMOTED", selected, flush=True)
    elif args.promote:
        print("NOT PROMOTED: validation quality guard failed", flush=True)
    print(json.dumps(metrics, indent=2), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
