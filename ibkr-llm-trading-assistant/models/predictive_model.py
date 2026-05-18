"""Predictive model wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import GradientBoostingClassifier

from config.settings import get_settings
from models.feature_engineering import FEATURE_COLUMNS, add_technical_features, create_target

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


class PredictiveModel:
    """
    ML model for next-period direction prediction.
    Does not guarantee profits — scores setups for risk filtering.
    """

    def __init__(self, model_name: str = "direction_classifier"):
        self.model_name = model_name
        self.model: Optional[object] = None
        self.feature_columns: list[str] = []
        self.settings = get_settings()

    def _build_model(self):
        if HAS_LIGHTGBM:
            return lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.05,
                random_state=42,
                verbose=-1,
            )
        return GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        )

    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        enriched = add_technical_features(df)
        target = create_target(enriched)
        available = [c for c in FEATURE_COLUMNS if c in enriched.columns]
        self.feature_columns = available
        X = enriched[available].dropna()
        y = target.loc[X.index].dropna()
        common = X.index.intersection(y.index)
        return X.loc[common], y.loc[common]

    def train(self, df: pd.DataFrame) -> dict:
        X, y = self.prepare_data(df)
        if len(X) < 100:
            raise ValueError("Insufficient data for training (need 100+ bars)")
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        self.model = self._build_model()
        self.model.fit(X_train, y_train)
        train_acc = float(self.model.score(X_train, y_train))
        test_acc = float(self.model.score(X_test, y_test))
        logger.info("Model trained: train_acc={:.3f} test_acc={:.3f}", train_acc, test_acc)
        return {"train_accuracy": train_acc, "test_accuracy": test_acc, "samples": len(X)}

    def predict_proba(self, df: pd.DataFrame) -> float:
        if self.model is None:
            raise RuntimeError("Model not trained or loaded")
        enriched = add_technical_features(df)
        available = [c for c in self.feature_columns if c in enriched.columns]
        if not available:
            available = [c for c in FEATURE_COLUMNS if c in enriched.columns]
        row = enriched[available].iloc[-1:].dropna(axis=1)
        if row.empty:
            return 0.5
        proba = self.model.predict_proba(row)[0]
        return float(max(proba))

    def score_setup(self, df: pd.DataFrame, direction: str = "long") -> float:
        """Score trade setup confidence (0-1)."""
        prob_up = self.predict_proba(df)
        if direction == "long":
            return prob_up
        return 1.0 - prob_up

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or self.settings.models_dir / f"{self.model_name}.joblib"
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model": self.model, "features": self.feature_columns, "name": self.model_name},
            path,
        )
        logger.info("Model saved to {}", path)
        return path

    def load(self, path: Optional[Path] = None) -> None:
        path = path or self.settings.models_dir / f"{self.model_name}.joblib"
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_columns = data["features"]
        logger.info("Model loaded from {}", path)
