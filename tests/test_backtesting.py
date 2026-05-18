from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.engine import BacktestConfig, BacktestEngine
from strategies.base_strategy import BaseStrategy, StrategySignal


class TestStrategy(BaseStrategy):
    name = "test_strategy"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

    def get_entry(self, row: pd.Series) -> float:
        return float(row["close"])

    def get_exit(self, row: pd.Series) -> float:
        return float(row["close"])

    def get_stop_loss(self, row: pd.Series, direction: str) -> float:
        return float(row["close"] - 1)

    def get_take_profit(self, row: pd.Series, direction: str) -> float:
        return float(row["close"] + 2)

    def generate_signal(self, data: pd.DataFrame, symbol: str, asset_class: str, timeframe: str):
        if len(data) % 10 == 0:
            row = data.iloc[-1]
            return StrategySignal(
                symbol=symbol,
                asset_class=asset_class,
                timeframe=timeframe,
                direction="long",
                entry_price=float(row["close"]),
                stop_loss=float(row["close"] - 1),
                take_profit=float(row["close"] + 2),
                confidence_score=0.8,
                reason="test signal",
                strategy_name=self.name,
                timestamp=data.index[-1].to_pydatetime(),
            )
        return None


def make_bars(n: int = 200) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    base = np.linspace(100, 130, n)
    bars = pd.DataFrame(
        {
            "open": base,
            "high": base + 1.5,
            "low": base - 1.5,
            "close": base + np.sin(np.arange(n) / 5),
            "volume": np.random.default_rng(1).integers(1000, 5000, size=n),
        },
        index=idx,
    )
    return bars


def test_backtest_runs_and_returns_metrics():
    bars = make_bars(220)
    engine = BacktestEngine(config=BacktestConfig(initial_capital=10_000, commission_per_trade=0.0, slippage_bps=0))
    result = engine.run(TestStrategy(), bars, symbol="SPY", asset_class="STK", timeframe="1 day")

    assert not result.equity_curve.empty
    assert "total_return" in result.metrics
    assert "num_trades" in result.metrics
    assert result.metrics["num_trades"] >= 1


def test_backtest_compare_strategies():
    bars = make_bars(180)
    engine = BacktestEngine()
    comparison = engine.compare_strategies(
        strategies={"t": TestStrategy()},
        bars_by_symbol={"SPY": bars, "QQQ": bars.copy()},
        asset_class="STK",
        timeframe="1 day",
    )
    assert len(comparison) == 2
    assert {"strategy", "symbol", "expectancy"}.issubset(set(comparison.columns))
