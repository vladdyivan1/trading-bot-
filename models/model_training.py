"""Model training and walk-forward validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from models.feature_engineering import make_training_set
from models.predictive_model import PredictiveModel


def walk_forward_train(
    bars: pd.DataFrame,
    model_path: str = "models/latest_model.joblib",
    n_splits: int = 5,
) -> dict:
    X, y, _ = make_training_set(bars)
    if len(X) < 200:
        raise ValueError("Not enough rows for robust model training")

    splitter = TimeSeriesSplit(n_splits=n_splits)
    scores: list[float] = []

    for train_idx, test_idx in splitter.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        model = PredictiveModel()
        model.fit(X_train, y_train)
        score = model.score_accuracy(X_test, y_test)
        scores.append(score)

    final_model = PredictiveModel()
    final_model.fit(X, y)

    target = Path(model_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    final_model.save(target)

    return {
        "rows": int(len(X)),
        "n_splits": n_splits,
        "fold_accuracies": [float(s) for s in scores],
        "mean_accuracy": float(np.mean(scores)) if scores else 0.0,
        "model_path": str(target),
    }
