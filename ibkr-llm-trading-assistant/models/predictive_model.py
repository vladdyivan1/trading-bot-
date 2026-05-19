"""Predictive model wrapper."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from models.feature_engineering import build_features


class PredictiveModel:
    """
    Classifier for next-bar direction.

    Does not guarantee profits — scores setups for risk-adjusted filtering.
    """

    def __init__(self, model_path: Path | None = None) -> None:
        self.model: GradientBoostingClassifier | None = None
        self.feature_columns: list[str] = []
        self.model_path = model_path

    def prepare_xy(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        features = build_features(df)
        close = df["close"] if "close" in df.columns else df["Close"]
        close = close.reindex(features.index)
        target = (close.shift(-1) > close).astype(int)
        target = target.reindex(features.index)
        aligned = features.join(target.rename("target")).dropna()
        X = aligned.drop(columns=["target"])
        y = aligned["target"]
        self.feature_columns = list(X.columns)
        return X, y

    def train(self, df: pd.DataFrame) -> dict:
        X, y = self.prepare_xy(df)
        if len(X) < 100:
            raise ValueError("Insufficient data for training (need 100+ bars)")
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        )
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        self.model.fit(X_train, y_train)
        train_acc = float(self.model.score(X_train, y_train))
        test_acc = float(self.model.score(X_test, y_test)) if len(X_test) else 0.0
        return {"train_accuracy": train_acc, "test_accuracy": test_acc, "samples": len(X)}

    def predict_proba(self, df: pd.DataFrame) -> float:
        if self.model is None:
            raise RuntimeError("Model not trained")
        features = build_features(df)
        if features.empty:
            return 0.5
        row = features.iloc[[-1]][self.feature_columns]
        proba = self.model.predict_proba(row)[0]
        # proba[1] = probability of up move
        return float(proba[1]) if len(proba) > 1 else 0.5

    def score_setup(self, df: pd.DataFrame) -> float:
        """Return confidence score 0-1 for long bias; invert for shorts externally."""
        return self.predict_proba(df)

    def save(self, path: Path) -> None:
        if self.model is None:
            raise RuntimeError("No model to save")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "columns": self.feature_columns}, path)

    def load(self, path: Path) -> None:
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_columns = data["columns"]
