"""Registry for strategy discovery and construction."""

from __future__ import annotations

from typing import Any, Type

from strategies.base_strategy import BaseStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIMeanReversionStrategy


class StrategyRegistry:
    """Simple registry for strategy classes."""

    def __init__(self) -> None:
        self._strategies: dict[str, Type[BaseStrategy]] = {}

    def register(self, strategy_cls: Type[BaseStrategy]) -> None:
        self._strategies[strategy_cls.name] = strategy_cls

    def create(self, name: str, **kwargs: Any) -> BaseStrategy:
        if name not in self._strategies:
            raise KeyError(f"Unknown strategy: {name}")
        return self._strategies[name](**kwargs)

    def names(self) -> list[str]:
        return sorted(self._strategies)


registry = StrategyRegistry()
registry.register(MovingAverageCrossoverStrategy)
registry.register(RSIMeanReversionStrategy)
registry.register(BreakoutStrategy)
