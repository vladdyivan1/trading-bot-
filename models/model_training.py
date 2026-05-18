"""Model training and walk-forward validation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtesting.walk_forward import rolling_splits
from models.feature_engineering import make_supervised_dataset
from models.predictive_model import ModelScore, PredictiveModel


@dataclass
class TrainingResult:
    model: PredictiveModel
    scores: list[ModelScore]


def train_predictive_model(data: pd.DataFrame, task: str = "direction", horizon: int = 1) -> PredictiveModel:
    X, y = make_supervised_dataset(data, horizon=horizon, target=task)
    model = PredictiveModel(task=task)
    model.fit(X, y)
    return model


def walk_forward_validate_model(
    data: pd.DataFrame,
    train_size: int,
    test_size: int,
    task: str = "direction",
    horizon: int = 1,
) -> TrainingResult:
    """Run chronological validation to avoid lookahead bias."""

    scores: list[ModelScore] = []
    final_model: PredictiveModel | None = None
    for split in rolling_splits(data, train_size=train_size, test_size=test_size):
        X_train, y_train = make_supervised_dataset(split.train, horizon=horizon, target=task)
        X_test, y_test = make_supervised_dataset(split.test, horizon=horizon, target=task)
        if X_train.empty or X_test.empty:
            continue
        model = PredictiveModel(task=task)
        model.fit(X_train, y_train)
        scores.append(model.evaluate(X_test, y_test))
        final_model = model
    if final_model is None:
        final_model = train_predictive_model(data, task=task, horizon=horizon)
    return TrainingResult(model=final_model, scores=scores)
