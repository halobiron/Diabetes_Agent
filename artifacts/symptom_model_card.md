# Symptom screening model

- Source: UCI Early Stage Diabetes Risk Prediction (2020), DOI 10.24432/C5VG8H.
- URL: https://archive.ics.uci.edu/dataset/529/early+stage+diabetes+risk+
- License: CC BY 4.0. Single-hospital questionnaire data, Sylhet, Bangladesh.
- 520 source rows; 251 distinct profiles after deduplication before splitting.
- Split seed 42: 150 training / 50 validation / 51 holdout profiles; no profile overlap.
- Inputs: age, sex, 14 explicitly answered symptom/state questions. Unknown is not No.
- Runtime range: age 16–90. BMI and systolic BP are still required by the surrounding
  application for reference displays and safety rules, but are not model features here.

## Model and operating point

Random Forest (400 trees, min_samples_leaf=2, max_features=0.8, seed 42), sigmoid
probability calibration with three-fold CV within training. User-approved threshold 0.5.

| Threshold | Precision | Recall | Accuracy | TP | FN | FP | TN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Initial 0.75734 | 1.0000 | 0.7143 | 0.8039 | 25 | 10 | 0 | 16 |
| Active 0.5 | 0.8889 | 0.9143 | 0.8627 | 32 | 3 | 4 | 12 |

The 0.5 point was adopted after retrospective holdout review. These are reused
holdout comparisons, not new independent test results. The initial failed recall
gate is summarized in the table above; active metrics are in
`symptom_metrics.json`. Intermediate experiment outputs were deleted during cleanup.

95% Wilson intervals: precision [0.7469, 0.9559], recall [0.7762, 0.9704].
Always-positive baseline on this holdout: precision 0.6863, recall 1, specificity 0.
The active model has specificity 0.75. Population prevalence strongly affects precision.

## Scope

Educational prototype, not a diagnostic device. This is a separate task/dataset
from BRFSS. No external or Vietnamese population validation has been performed.
The high scores do not guarantee individual or future performance. Neither a Low
score nor negative model flag rules out diabetes.

Additional nested internal CV of the selection procedure (not this single final
RF model) is recorded separately in `symptom_cv_metrics.json`.

The symptom training and nested-CV scripts were removed during cleanup.
The active model and retained metrics remain available; rerunning training requires
restoring the scripts from version control.

Verification: 220 backend tests passed, 7 warnings; web typecheck, lint, 7 tests
and production build passed. Browser flows passed at desktop/mobile widths,
with no degraded components or JavaScript errors and successful profile restore.
The intermediate verification log was deleted during cleanup. These are historical
verification results, not a new run. Coverage was not remeasured.
