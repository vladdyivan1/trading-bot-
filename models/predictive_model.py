"""Predictive model wrapper with persistence and scoring."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


class PredictiveModel:
    def __init__(self, model=None, feature_columns: list[str] | None = None) -> None:
        self.model = model or RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            random_state=42,
            n_jobs=-1,
        )
        self.feature_columns = feature_columns or []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_columns = list(X.columns)
        self.model.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        data = X[self.feature_columns]
        proba = self.model.predict_proba(data)[:, 1]
        return pd.Series(proba, index=data.index)

    def predict_direction(self, X: pd.DataFrame, threshold: float = 0.5) -> pd.Series:
        proba = self.predict_proba(X)
        return (proba >= threshold).astype(int)

    def score_accuracy(self, X: pd.DataFrame, y: pd.Series, threshold: float = 0.5) -> float:
        pred = self.predict_direction(X, threshold=threshold)
        return float((pred == y).mean())

    def save(self, path: str | Path) -> None:
        payload = {
            "model": self.model,
            "feature_columns": self.feature_columns,
        }
        joblib.dump(payload, path)

    @classmethod
    def load(cls, path: str | Path) -> "PredictiveModel":
        payload = joblib.load(path)
        return cls(model=payload["model"], feature_columns=payload["feature_columns"])
