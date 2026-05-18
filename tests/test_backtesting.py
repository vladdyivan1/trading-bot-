import pandas as pd
import pytest

from backtesting.engine import BacktestEngine
from strategies.base_strategy import BaseStrategy, TradeSignal


class OneShotStrategy(BaseStrategy):
    name = "one_shot"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.copy()

    def generate_signal(self, data: pd.DataFrame) -> TradeSignal | None:
        if len(data) == 2:
            return TradeSignal(
                symbol="SPY",
                asset_class="STK",
                timeframe="1 day",
                direction="long",
                entry_price=float(data.iloc[-1]["close"]),
                stop_loss=9.0,
                take_profit=12.0,
                confidence_score=0.8,
                reason="test signal",
            )
        return None


def test_backtest_tracks_take_profit_trade_and_metrics():
    data = pd.DataFrame(
        {
            "open": [10, 10, 10],
            "high": [10.5, 10.5, 12.5],
            "low": [9.5, 9.5, 9.8],
            "close": [10, 10, 12],
            "volume": [100, 100, 100],
        },
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    engine = BacktestEngine(initial_capital=10_000, commission_per_share=0, slippage_bps=0, risk_fraction=0.005)

    result = engine.run(data, OneShotStrategy("SPY"))

    assert len(result.trades) == 1
    assert result.trades[0]["exit_reason"] == "take_profit"
    assert result.trades[0]["pnl"] == 100
    assert result.equity_curve.iloc[-1] == 10_100
    assert result.metrics["number_of_trades"] == 1
    assert result.metrics["win_rate"] == 1
    assert result.metrics["total_return"] == pytest.approx(0.01)
