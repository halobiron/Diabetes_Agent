"""Sklearn-compatible MLP trained with PyTorch, served with NumPy.

Training needs torch (GPU if available). Prediction is a plain NumPy forward
pass over the stored weights, so a saved artifact loads and runs without torch.
"""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class TorchMLPClassifier(ClassifierMixin, BaseEstimator):
    def __init__(
        self,
        hidden_layers=(128, 64),
        dropout=0.2,
        learning_rate=1e-3,
        weight_decay=1e-4,
        epochs=40,
        batch_size=2048,
        patience=5,
        validation_fraction=0.1,
        random_state=42,
    ):
        self.hidden_layers = hidden_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.epochs = epochs
        self.batch_size = batch_size
        self.patience = patience
        self.validation_fraction = validation_fraction
        self.random_state = random_state

    def fit(self, X, y):
        import torch
        from torch import nn

        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        self.classes_ = np.array([0, 1])

        rng = np.random.default_rng(self.random_state)
        torch.manual_seed(self.random_state)
        order = rng.permutation(len(X))
        n_val = max(1, int(len(X) * self.validation_fraction))
        val_idx, train_idx = order[:n_val], order[n_val:]

        device = "cuda" if torch.cuda.is_available() else "cpu"
        X_train = torch.tensor(X[train_idx], device=device)
        y_train = torch.tensor(y[train_idx], device=device)
        X_val = torch.tensor(X[val_idx], device=device)
        y_val = torch.tensor(y[val_idx], device=device)

        layers, width = [], X.shape[1]
        for units in self.hidden_layers:
            layers += [nn.Linear(width, units), nn.ReLU(), nn.Dropout(self.dropout)]
            width = units
        layers.append(nn.Linear(width, 1))
        net = nn.Sequential(*layers).to(device)

        # Same class balancing as the other candidates; calibration restores probabilities.
        positives = float(y_train.sum().item())
        pos_weight = torch.tensor((len(y_train) - positives) / max(positives, 1.0), device=device)
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        optimizer = torch.optim.AdamW(
            net.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
        )

        best_loss, best_state, stale = float("inf"), None, 0
        for _ in range(self.epochs):
            net.train()
            permutation = torch.randperm(len(X_train), device=device)
            for start in range(0, len(permutation), self.batch_size):
                batch = permutation[start : start + self.batch_size]
                optimizer.zero_grad()
                loss = loss_fn(net(X_train[batch]).squeeze(1), y_train[batch])
                loss.backward()
                optimizer.step()

            net.eval()
            with torch.no_grad():
                val_loss = loss_fn(net(X_val).squeeze(1), y_val).item()
            if val_loss < best_loss - 1e-5:
                best_loss, stale = val_loss, 0
                best_state = [p.detach().cpu().numpy().copy() for p in net.parameters()]
            else:
                stale += 1
                if stale >= self.patience:
                    break

        # Parameters alternate weight (out, in) / bias (out,); store as (in, out) for NumPy.
        self.weights_ = [
            (best_state[i].T.astype(np.float64), best_state[i + 1].astype(np.float64))
            for i in range(0, len(best_state), 2)
        ]
        self.n_features_in_ = X.shape[1]
        return self

    def predict_proba(self, X):
        activations = np.asarray(X, dtype=np.float64)
        for i, (weight, bias) in enumerate(self.weights_):
            activations = activations @ weight + bias
            if i < len(self.weights_) - 1:
                activations = np.maximum(activations, 0.0)
        positive = 1.0 / (1.0 + np.exp(-activations[:, 0]))
        return np.column_stack([1.0 - positive, positive])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
