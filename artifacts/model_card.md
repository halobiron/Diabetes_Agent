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

- Selection: 5-fold_cv_tuning_then_validation_selection_then_holdout_test
- Hyperparameter tuning: hist_gradient_boosting, mlp
- Probability calibration: isotonic_cv3
- LightGBM included: True

## Selected Model

- Model: `mlp`
- CV ROC AUC: 0.83049 (+/- 0.00239)
- Validation ROC AUC (selection): 0.82828
- Holdout test ROC AUC: 0.82581
- Average precision: 0.41441
- Brier score: 0.09783
- Threshold (chosen on validation): 0.23906
- Test F1 at that threshold: 0.46543
- Test precision / recall: 0.37906 / 0.60277
