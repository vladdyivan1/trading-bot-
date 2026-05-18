"""Strategy registry for dynamic strategy selection."""

from __future__ import annotations

from strategies.base_strategy import BaseStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy

STRATEGY_REGISTRY = {
    "moving_average_crossover": MovingAverageStrategy,
    "rsi_mean_reversion": RSIStrategy,
    "breakout": BreakoutStrategy,
}


def available_strategies() -> list[str]:
    return sorted(STRATEGY_REGISTRY.keys())


def build_strategy(name: str, **kwargs) -> BaseStrategy:
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}")
    return cls(**kwargs)
