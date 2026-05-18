"""Deterministic backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from backtesting.metrics import compute_metrics
from schemas import BacktestMetrics, Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_per_trade: float = 1.0
    slippage_pct: float = 0.0005
    position_size_pct: float = 0.1
    bars_per_year: int = 252


@dataclass
class BacktestResult:
    metrics: BacktestMetrics
    trades: pd.DataFrame
    equity_curve: pd.Series
    strategy_name: str
    symbol: str


class BacktestEngine:
    """Bar-by-bar backtester with stops, targets, and costs."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        symbol: str = "SPY",
    ) -> BacktestResult:
        data = strategy.calculate_indicators(df.copy())
        if "close" not in data.columns and "Close" in data.columns:
            data = data.rename(columns={"Close": "close", "High": "high", "Low": "low", "Open": "open"})

        capital = self.config.initial_capital
        equity = [capital]
        equity_index = [data.index[0] if len(data.index) else 0]
        trades: list[dict] = []
        position: dict | None = None

        warmup = max(50, getattr(strategy, "slow", 30) if hasattr(strategy, "slow") else 30)

        for i in range(warmup, len(data)):
            window = data.iloc[: i + 1]
            bar = data.iloc[i]
            close = float(bar["close"])
            bar_time = data.index[i]

            if position:
                exit_price, reason = self._check_exit(position, bar)
                if exit_price is not None:
                    slip = exit_price * self.config.slippage_pct
                    if position["direction"] == Direction.LONG:
                        exit_price -= slip
                    else:
                        exit_price += slip
                    pnl = self._calc_pnl(position, exit_price)
                    capital += pnl - self.config.commission_per_trade
                    trades.append(
                        {
                            "entry_time": position["entry_time"],
                            "exit_time": bar_time,
                            "direction": position["direction"].value,
                            "entry_price": position["entry_price"],
                            "exit_price": exit_price,
                            "pnl": pnl,
                            "hold_bars": i - position["entry_bar"],
                            "reason": reason,
                        }
                    )
                    position = None

            if position is None:
                window.attrs = {}
                signal = strategy.generate_signal(window)
                if signal and signal.direction != Direction.FLAT:
                    entry = close * (1 + self.config.slippage_pct * (1 if signal.direction == Direction.LONG else -1))
                    size = capital * self.config.position_size_pct
                    qty = size / entry if entry > 0 else 0
                    position = {
                        "direction": signal.direction,
                        "entry_price": entry,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "entry_time": bar_time,
                        "entry_bar": i,
                        "quantity": qty,
                    }

            equity.append(capital)
            equity_index.append(bar_time)

        if position:
            close = float(data.iloc[-1]["close"])
            pnl = self._calc_pnl(position, close)
            capital += pnl - self.config.commission_per_trade
            trades.append(
                {
                    "entry_time": position["entry_time"],
                    "exit_time": data.index[-1],
                    "direction": position["direction"].value,
                    "entry_price": position["entry_price"],
                    "exit_price": close,
                    "pnl": pnl,
                    "hold_bars": len(data) - position["entry_bar"],
                    "reason": "end_of_data",
                }
            )
            equity[-1] = capital

        trades_df = pd.DataFrame(trades)
        equity_series = pd.Series(equity, index=pd.Index(equity_index[: len(equity)]))
        metrics = compute_metrics(trades_df, equity_series, self.config.bars_per_year)

        return BacktestResult(
            metrics=metrics,
            trades=trades_df,
            equity_curve=equity_series,
            strategy_name=strategy.name,
            symbol=symbol,
        )

    def _check_exit(self, position: dict, bar: pd.Series) -> tuple[float | None, str]:
        high = float(bar["high"])
        low = float(bar["low"])
        close = float(bar["close"])
        d = position["direction"]
        sl = position["stop_loss"]
        tp = position["take_profit"]

        if d == Direction.LONG:
            if low <= sl:
                return sl, "stop_loss"
            if high >= tp:
                return tp, "take_profit"
        else:
            if high >= sl:
                return sl, "stop_loss"
            if low <= tp:
                return tp, "take_profit"
        return None, ""

    def _calc_pnl(self, position: dict, exit_price: float) -> float:
        qty = position["quantity"]
        entry = position["entry_price"]
        if position["direction"] == Direction.LONG:
            return (exit_price - entry) * qty
        return (entry - exit_price) * qty

    def compare_strategies(
        self,
        strategies: list[BaseStrategy],
        df: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        rows = []
        for strat in strategies:
            result = self.run(strat, df, symbol)
            m = result.metrics
            rows.append(
                {
                    "strategy": strat.name,
                    "symbol": symbol,
                    "total_return": m.total_return,
                    "sharpe": m.sharpe_ratio,
                    "max_drawdown": m.max_drawdown,
                    "win_rate": m.win_rate,
                    "num_trades": m.num_trades,
                    "expectancy": m.expectancy,
                }
            )
        return pd.DataFrame(rows)
