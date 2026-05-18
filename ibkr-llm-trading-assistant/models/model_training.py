"""Model training with walk-forward validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import get_settings
from models.predictive_model import PredictiveModel


class ModelTrainer:
    def __init__(self, models_dir: Path | None = None) -> None:
        settings = get_settings()
        self.models_dir = models_dir or settings.models_dir

    def train_and_save(self, df: pd.DataFrame, symbol: str) -> dict:
        model = PredictiveModel()
        metrics = model.train(df)
        path = self.models_dir / f"{symbol}_direction.joblib"
        model.save(path)
        metrics["model_path"] = str(path)
        return metrics

    def walk_forward_train(
        self,
        df: pd.DataFrame,
        train_size: int = 252,
        test_size: int = 63,
    ) -> list[dict]:
        """Walk-forward model evaluation without lookahead."""
        results = []
        start = 0
        while start + train_size + test_size <= len(df):
            train_df = df.iloc[start : start + train_size]
            test_df = df.iloc[start + train_size : start + train_size + test_size]
            model = PredictiveModel()
            try:
                metrics = model.train(train_df)
                # Score on test period bar by bar using only past data
                accs = []
                for i in range(50, len(test_df)):
                    window = pd.concat([train_df, test_df.iloc[: i + 1]])
                    pred = model.predict_proba(window)
                    actual = float(test_df["close"].iloc[i] > test_df["close"].iloc[i - 1])
                    accs.append((pred >= 0.5) == actual)
                metrics["walk_forward_accuracy"] = sum(accs) / len(accs) if accs else 0
                results.append(metrics)
            except ValueError:
                pass
            start += test_size
        return results
