"""Baseline predictive model wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass
class ModelScore:
    metric_name: str
    value: float
    samples: int


class PredictiveModel:
    """Scikit-learn model for next-period direction or return prediction."""

    def __init__(self, task: str = "direction", random_state: int = 42) -> None:
        if task not in {"direction", "return"}:
            raise ValueError("task must be 'direction' or 'return'")
        self.task = task
        estimator = (
            RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=random_state)
            if task == "direction"
            else RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=random_state)
        )
        self.pipeline = Pipeline([("scaler", StandardScaler()), ("model", estimator)])
        self.feature_names: list[str] = []
        self.latest_score: ModelScore | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_names = list(X.columns)
        self.pipeline.fit(X, y)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        self._validate_features(X)
        return pd.Series(self.pipeline.predict(X[self.feature_names]), index=X.index)

    def score_setups(self, X: pd.DataFrame) -> pd.Series:
        """Return confidence/probability for positive direction or scaled regression sign."""

        self._validate_features(X)
        model = self.pipeline.named_steps["model"]
        if self.task == "direction" and hasattr(model, "predict_proba"):
            probabilities = self.pipeline.predict_proba(X[self.feature_names])[:, 1]
            return pd.Series(probabilities, index=X.index)
        predictions = self.pipeline.predict(X[self.feature_names])
        return pd.Series(predictions, index=X.index)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> ModelScore:
        predictions = self.predict(X)
        if self.task == "direction":
            value = float(accuracy_score(y, predictions))
            metric = "accuracy"
        else:
            value = float(mean_squared_error(y, predictions, squared=False))
            metric = "rmse"
        self.latest_score = ModelScore(metric, value, len(y))
        return self.latest_score

    def save(self, path: str | Path) -> None:
        joblib.dump({"pipeline": self.pipeline, "feature_names": self.feature_names, "task": self.task}, path)

    @classmethod
    def load(cls, path: str | Path) -> "PredictiveModel":
        payload: dict[str, Any] = joblib.load(path)
        model = cls(task=payload["task"])
        model.pipeline = payload["pipeline"]
        model.feature_names = payload["feature_names"]
        return model

    def _validate_features(self, X: pd.DataFrame) -> None:
        missing = set(self.feature_names) - set(X.columns)
        if missing:
            raise ValueError(f"Missing model features: {sorted(missing)}")
