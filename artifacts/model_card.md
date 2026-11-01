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
- Hyperparameter tuning: hist_gradient_boosting, lightgbm
- Probability calibration: isotonic_cv3
- LightGBM included: True

## Selected Model

- Model: `lightgbm`
- CV ROC AUC: 0.82839 (+/- 0.00244)
- Validation ROC AUC (selection): 0.8279
- Holdout test ROC AUC: 0.82666
- Average precision: 0.42163
- Brier score: 0.09746
- Threshold (chosen on validation): 0.26146
- Test F1 at that threshold: 0.46642
- Test precision / recall: 0.39553 / 0.56826
