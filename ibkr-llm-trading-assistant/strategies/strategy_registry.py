"""Strategy registry for discovery and ranking."""

from __future__ import annotations

from typing import Type

from strategies.base_strategy import BaseStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy

_REGISTRY: dict[str, Type[BaseStrategy]] = {
    MovingAverageStrategy.name: MovingAverageStrategy,
    RSIStrategy.name: RSIStrategy,
    BreakoutStrategy.name: BreakoutStrategy,
}


def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    _REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str, params: dict | None = None) -> BaseStrategy:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy: {name}. Available: {list(_REGISTRY)}")
    return _REGISTRY[name](params)


def list_strategies() -> list[str]:
    return list(_REGISTRY.keys())
