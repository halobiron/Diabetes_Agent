import pickle

import numpy as np
import pytest
from sklearn.metrics import precision_score, recall_score

from models.screening import ProbabilityEnsemble, screening_threshold, select_screening_candidate


def test_reject_candidates_meeting_only_one_required_target():
    results = {
        "recall_only": {
            "precision": 0.304,
            "recall": 0.8,
            "average_precision": 0.43,
            "roc_auc": 0.83,
        },
        "precision_only": {
            "precision": 0.5,
            "recall": 0.318,
            "average_precision": 0.43,
            "roc_auc": 0.83,
        },
    }
    with pytest.raises(ValueError, match="No candidate meets"):
        select_screening_candidate(results)


def test_select_only_candidate_meeting_both_required_targets():
    results = {
        "wrong": {"precision": 0.9, "recall": 0.79, "average_precision": 0.7, "roc_auc": 0.9},
        "right": {"precision": 0.5, "recall": 0.8, "average_precision": 0.5, "roc_auc": 0.85},
    }
    assert select_screening_candidate(results) == "right"


def test_reject_precision_just_below_target_without_rounding():
    results = {
        "below": {"precision": 0.4999999, "recall": 0.81, "average_precision": 0.5, "roc_auc": 0.8}
    }
    with pytest.raises(ValueError):
        select_screening_candidate(results)


def test_recall_constraint_uses_feasible_threshold_with_best_precision():
    y = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    p = np.array([0.9, 0.85, 0.8, 0.7, 0.6, 0.5, 0.4, 0.1])
    threshold = screening_threshold(y, p, 0.75)
    assert recall_score(y, p >= threshold) >= 0.75
    feasible = [t for t in np.unique(p) if recall_score(y, p >= t) >= 0.75]
    assert precision_score(y, p >= threshold) == max(precision_score(y, p >= t) for t in feasible)


def test_plateau_threshold_preserves_all_ties_without_rounding():
    y = np.array([0, 1, 1, 1])
    p = np.array([0.1, 0.13962816208078224, 0.13962816208078224, 0.9])
    threshold = screening_threshold(y, p, 1.0)
    assert threshold == p[1]
    assert recall_score(y, p >= threshold) == 1.0


@pytest.mark.parametrize("target", [0, -0.1, 1.1])
def test_invalid_recall_target_is_rejected(target):
    with pytest.raises(ValueError):
        screening_threshold([0, 1], [0.1, 0.9], target)


@pytest.mark.parametrize(
    "y,p", [([0, 0], [0.1, 0.2]), ([0, 1], [0.1, np.nan]), ([0, 1], [0.1, 1.1]), ([1], [0.1, 0.2])]
)
def test_invalid_evaluation_data_is_rejected(y, p):
    with pytest.raises(ValueError):
        screening_threshold(y, p)


class ConstantModel:
    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, X):
        return np.tile([1 - self.probability, self.probability], (len(X), 1))


def test_ensemble_survives_serialization_and_normalizes_weights():
    model = ProbabilityEnsemble([ConstantModel(0.2), ConstantModel(0.8)], [3, 1])
    restored = pickle.loads(pickle.dumps(model))
    np.testing.assert_allclose(restored.predict_proba(np.zeros((2, 3))), [[0.65, 0.35]] * 2)
