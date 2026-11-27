# Healthcare Diabetes Risk Model Card

## Intended Use

This model estimates diabetes risk from CDC BRFSS health indicators for an educational
healthcare AI prototype. It is not a diagnostic medical device.

## Dataset

- Source: Kaggle `alexteboul/diabetes-health-indicators-dataset`
- Target: `Diabetes_binary`
- Rows: 253680
- Features: 21

## Training

- Selection: maximum validation precision subject to recall target; AP then AUC tie-break
- Hyperparameter tuning: lightgbm_six_configurations, mlp_blend_weights
- Probability calibration: baseline isotonic_cv3; new LightGBM isotonic on internal training calibration split
- LightGBM included: True

## Selected Model

- Model: `blend_mlp0.75_lgbm_leaves31_l2_20_balanced0`
- CV ROC AUC: not measured for this ensemble; selected on validation
- Validation ROC AUC (selection): 0.82897
- Holdout test ROC AUC: 0.82663
- Average precision: 0.41893
- Brier score: 0.09755
- Threshold (chosen on validation): 0.14146671639492997
- Test F1 at that threshold: 0.44042
- Test precision / recall: 0.30385 / 0.79997

## Operating-point tradeoff

The experimental target is recall >= 0.80 on validation, maximizing precision
subject to this constraint. This is not a clinically approved target.
The historical test split is reused for a paired comparison, not a new external
validation set. Active model metrics are in `artifacts/metrics.json`.
Historical experiment outputs and the separate baseline artifact were deleted
during cleanup; exact replay requires supplying the original MLP baseline again.
Higher recall comes with more false positives and lower precision/accuracy/F1
at the screening threshold. Ranking gains are small; do not describe them as a
large model improvement. Historical integration tests and screenshots predate
this artifact and must not be represented as reruns of the optimized model.

## Regression verification

- Passed: 204
- Warnings: 7
- Duration: 297.03 seconds
- Includes real local Neo4j and API acceptance tests.
- Coverage was not remeasured in this run.
