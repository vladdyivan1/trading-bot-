"""Deterministic single-asset backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from backtesting.metrics import summarize_backtest_metrics
from strategies.base_strategy import BaseStrategy


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_per_trade: float = 1.0
    slippage_bps: float = 1.0
    position_size: int = 1


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict


class BacktestEngine:
    """Backtesting engine with stops and targets."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
    ) -> BacktestResult:
        if bars.empty:
            empty_trades = pd.DataFrame(columns=["entry_time", "exit_time", "direction", "entry", "exit", "quantity", "pnl", "hold_time", "exit_reason"])
            equity_df = pd.DataFrame({"equity": [self.config.initial_capital]}, index=[pd.Timestamp.utcnow()])
            return BacktestResult(trades=empty_trades, equity_curve=equity_df, metrics=summarize_backtest_metrics(empty_trades, equity_df["equity"]))

        data = bars.sort_index().copy()
        capital = self.config.initial_capital
        equity_points: list[tuple[pd.Timestamp, float]] = []
        trades: list[dict] = []

        position: dict | None = None

        for i in range(1, len(data)):
            ts = data.index[i]
            row = data.iloc[i]
            history = data.iloc[: i + 1]

            if position is not None:
                exit_price = None
                exit_reason = None

                if position["direction"] == "long":
                    if float(row["low"]) <= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        exit_reason = "stop_loss"
                    elif float(row["high"]) >= position["take_profit"]:
                        exit_price = position["take_profit"]
                        exit_reason = "take_profit"
                else:
                    if float(row["high"]) >= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        exit_reason = "stop_loss"
                    elif float(row["low"]) <= position["take_profit"]:
                        exit_price = position["take_profit"]
                        exit_reason = "take_profit"

                if exit_price is not None:
                    side_mult = 1 if position["direction"] == "long" else -1
                    gross = (exit_price - position["entry"]) * side_mult * position["quantity"]
                    costs = self.config.commission_per_trade * 2
                    pnl = gross - costs
                    capital += pnl

                    trades.append(
                        {
                            "entry_time": position["entry_time"],
                            "exit_time": ts,
                            "direction": position["direction"],
                            "entry": position["entry"],
                            "exit": exit_price,
                            "quantity": position["quantity"],
                            "pnl": pnl,
                            "hold_time": ts - position["entry_time"],
                            "exit_reason": exit_reason,
                        }
                    )
                    position = None

            if position is None:
                signal = strategy.generate_signal(history, symbol=symbol, asset_class=asset_class, timeframe=timeframe)
                if signal is not None:
                    slip = signal.entry_price * (self.config.slippage_bps / 10_000)
                    entry_price = signal.entry_price + slip if signal.direction == "long" else signal.entry_price - slip
                    position = {
                        "entry_time": ts,
                        "direction": signal.direction,
                        "entry": entry_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "quantity": self.config.position_size,
                    }
                    capital -= self.config.commission_per_trade

            equity_points.append((ts, capital))

        if position is not None:
            final_ts = data.index[-1]
            final_price = float(data.iloc[-1]["close"])
            side_mult = 1 if position["direction"] == "long" else -1
            pnl = (final_price - position["entry"]) * side_mult * position["quantity"] - self.config.commission_per_trade
            capital += pnl
            trades.append(
                {
                    "entry_time": position["entry_time"],
                    "exit_time": final_ts,
                    "direction": position["direction"],
                    "entry": position["entry"],
                    "exit": final_price,
                    "quantity": position["quantity"],
                    "pnl": pnl,
                    "hold_time": final_ts - position["entry_time"],
                    "exit_reason": "end_of_data",
                }
            )
            equity_points.append((final_ts, capital))

        trades_df = pd.DataFrame(trades)
        if equity_points:
            equity_df = pd.DataFrame(equity_points, columns=["timestamp", "equity"]).set_index("timestamp")
        else:
            equity_df = pd.DataFrame({"equity": [capital]}, index=[data.index[-1]])

        metrics = summarize_backtest_metrics(trades_df, equity_df["equity"])
        return BacktestResult(trades=trades_df, equity_curve=equity_df, metrics=metrics)

    def compare_strategies(
        self,
        strategies: dict[str, BaseStrategy],
        bars_by_symbol: dict[str, pd.DataFrame],
        asset_class: str,
        timeframe: str,
    ) -> pd.DataFrame:
        rows = []
        for strategy_name, strategy in strategies.items():
            for symbol, bars in bars_by_symbol.items():
                result = self.run(strategy, bars, symbol=symbol, asset_class=asset_class, timeframe=timeframe)
                row = {"strategy": strategy_name, "symbol": symbol, **result.metrics}
                rows.append(row)
        return pd.DataFrame(rows).sort_values(["expectancy", "sharpe_ratio"], ascending=False)
