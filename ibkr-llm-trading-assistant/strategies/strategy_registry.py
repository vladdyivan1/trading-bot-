"""Strategy registry for discovery and comparison."""

from __future__ import annotations

from typing import Type

from strategies.base_strategy import BaseStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIMeanReversionStrategy

STRATEGY_REGISTRY: dict[str, Type[BaseStrategy]] = {
    "ma_crossover": MovingAverageCrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "breakout": BreakoutStrategy,
}


def get_strategy(name: str, symbol: str, **kwargs) -> BaseStrategy:
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](symbol=symbol, **kwargs)


def list_strategies() -> list[str]:
    return list(STRATEGY_REGISTRY.keys())
