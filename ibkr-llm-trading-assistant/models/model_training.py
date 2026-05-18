"""Model training with walk-forward validation."""

from __future__ import annotations

from typing import Any, List

import pandas as pd
from loguru import logger

from database.db import get_db_session
from database.models import ModelAccuracy
from models.predictive_model import PredictiveModel


class ModelTrainer:
    """Train and validate models without lookahead bias."""

    def __init__(self, train_window: int = 500, test_window: int = 100):
        self.train_window = train_window
        self.test_window = test_window

    def walk_forward_train(self, df: pd.DataFrame, symbol: str) -> dict[str, Any]:
        accuracies: List[float] = []
        start = 0
        fold = 0

        while start + self.train_window + self.test_window <= len(df):
            train_df = df.iloc[start : start + self.train_window]
            test_df = df.iloc[start + self.train_window : start + self.train_window + self.test_window]

            model = PredictiveModel(f"wf_{symbol}_{fold}")
            try:
                metrics = model.train(train_df)
                X_test, y_test = model.prepare_data(test_df)
                if len(X_test) > 0 and model.model:
                    acc = float(model.model.score(X_test, y_test))
                    accuracies.append(acc)
                    self._log_accuracy(symbol, model.model_name, acc, len(X_test))
            except ValueError as e:
                logger.warning("Walk-forward fold {} skipped: {}", fold, e)

            start += self.test_window
            fold += 1

        if not accuracies:
            return {"folds": 0, "mean_accuracy": 0.0}

        final_model = PredictiveModel(f"final_{symbol}")
        final_metrics = final_model.train(df)
        final_model.save()

        return {
            "folds": len(accuracies),
            "mean_accuracy": sum(accuracies) / len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "final_train_metrics": final_metrics,
        }

    def _log_accuracy(self, symbol: str, model_name: str, accuracy: float, sample_size: int) -> None:
        with get_db_session() as session:
            session.add(
                ModelAccuracy(
                    model_name=model_name,
                    symbol=symbol,
                    accuracy=accuracy,
                    sample_size=sample_size,
                )
            )
