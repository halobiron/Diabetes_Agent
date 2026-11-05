import pickle
import sys

import numpy as np
import pytest

pytest.importorskip("torch")

from models.mlp import TorchMLPClassifier  # noqa: E402


def _toy_data(n=600):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 5))
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(scale=0.3, size=n) > 0).astype(int)
    return X, y


def test_mlp_learns_and_returns_valid_probabilities():
    X, y = _toy_data()
    model = TorchMLPClassifier(
        hidden_layers=(16,), learning_rate=1e-2, epochs=60, batch_size=128
    ).fit(X, y)
    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert (model.predict(X) == y).mean() > 0.85


def test_mlp_predicts_after_pickle_without_torch(monkeypatch):
    X, y = _toy_data()
    model = TorchMLPClassifier(hidden_layers=(8,), epochs=5, batch_size=128).fit(X, y)
    expected = model.predict_proba(X)

    restored = pickle.loads(pickle.dumps(model))
    monkeypatch.setitem(sys.modules, "torch", None)  # any torch import now fails
    assert np.allclose(restored.predict_proba(X), expected)


def test_mlp_pipeline_calibrates_like_other_candidates():
    from sklearn.base import is_classifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    X, y = _toy_data()
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", TorchMLPClassifier(hidden_layers=(8,), epochs=5, batch_size=128)),
        ]
    )
    assert is_classifier(pipeline)
    calibrated = CalibratedClassifierCV(pipeline, method="isotonic", cv=3).fit(X, y)
    assert calibrated.predict_proba(X).shape == (len(X), 2)
