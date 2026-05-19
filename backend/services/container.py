from __future__ import annotations

from functools import lru_cache

from backend.services.decision_pipeline import DecisionPipeline


@lru_cache(maxsize=1)
def get_pipeline() -> DecisionPipeline:
    return DecisionPipeline()
