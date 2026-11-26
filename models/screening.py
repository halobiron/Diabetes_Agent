"""Validation-only operating-point selection and portable probability ensembles."""

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import precision_recall_curve


def screening_threshold(y_true, probabilities, minimum_recall=0.8):
    """Maximize precision subject to recall; break ties with the highest threshold.

    The target is an experiment setting, not a clinically validated requirement.
    Call with validation labels only. Return an observed score without rounding:
    rounding an isotonic plateau upward can change which cases are flagged.
    """
    if not 0 < minimum_recall <= 1:
        raise ValueError("minimum_recall must be in (0, 1].")
    y = np.asarray(y_true)
    p = np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.shape != y.shape or not len(y):
        raise ValueError("Labels and probabilities must be nonempty matching vectors.")
    if not np.isin(y, [0, 1]).all() or not (y == 1).any():
        raise ValueError("Binary labels must include a positive case.")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite and within [0, 1].")
    precision, recall, thresholds = precision_recall_curve(y, p)
    eligible = np.flatnonzero(recall[:-1] >= minimum_recall)
    index = max(eligible, key=lambda i: (precision[i], thresholds[i]))
    return float(thresholds[index])


def select_screening_candidate(results, minimum_recall=0.8, minimum_precision=0.5):
    """Reject infeasible searches before test evaluation or artifact promotion."""
    if not 0 < minimum_recall <= 1 or not 0 < minimum_precision <= 1:
        raise ValueError("Recall and precision targets must be in (0, 1].")
    eligible = {
        name: r
        for name, r in results.items()
        if r["recall"] >= minimum_recall and r["precision"] >= minimum_precision
    }
    if not eligible:
        raise ValueError(
            f"No candidate meets validation recall >= {minimum_recall:.1%} "
            f"and precision >= {minimum_precision:.1%}; artifacts must remain unchanged."
        )
    return max(
        eligible,
        key=lambda n: (
            eligible[n]["precision"],
            eligible[n]["average_precision"],
            eligible[n]["roc_auc"],
        ),
    )


class ProbabilityEnsemble(ClassifierMixin, BaseEstimator):
    """Blend already-fitted models without importing a training framework at runtime."""

    def __init__(self, estimators, weights):
        self.estimators = estimators
        self.weights = weights
        self.classes_ = np.array([0, 1])

    def predict_proba(self, X):
        weights = np.asarray(self.weights, dtype=float)
        if len(weights) != len(self.estimators) or (weights < 0).any() or weights.sum() <= 0:
            raise ValueError("Provide nonnegative weights with a positive total for all models.")
        p = sum(w * m.predict_proba(X)[:, 1] for w, m in zip(weights, self.estimators))
        p = p / weights.sum()
        return np.column_stack([1 - p, p])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
