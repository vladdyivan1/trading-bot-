"""Deterministic backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backtesting.metrics import calculate_trade_metrics
from strategies.base_strategy import BaseStrategy, TradeSignal


@dataclass
class BacktestResult:
    """Backtest output bundle."""

    trades: list[dict[str, Any]]
    equity_curve: pd.Series
    metrics: dict[str, float]
    signals: list[TradeSignal] = field(default_factory=list)

    def export_trades(self, path: str) -> None:
        pd.DataFrame(self.trades).to_csv(path, index=False)


@dataclass
class Position:
    direction: str
    quantity: int
    entry_price: float
    entry_time: Any
    entry_index: int
    stop_loss: float | None
    take_profit: float | None
    signal: TradeSignal


class BacktestEngine:
    """Single-position, bar-based backtesting engine."""

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_per_share: float = 0.005,
        slippage_bps: float = 1.0,
        risk_fraction: float = 0.005,
        periods_per_year: int = 252,
    ) -> None:
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.slippage_bps = slippage_bps
        self.risk_fraction = risk_fraction
        self.periods_per_year = periods_per_year

    def run(self, data: pd.DataFrame, strategy: BaseStrategy) -> BacktestResult:
        """Run a strategy on historical OHLCV bars without lookahead."""

        required = {"open", "high", "low", "close"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        if data.empty:
            raise ValueError("Cannot backtest empty data")

        bars = data.sort_index().copy()
        cash = self.initial_capital
        equity_values: list[float] = []
        equity_index: list[Any] = []
        trades: list[dict[str, Any]] = []
        signals: list[TradeSignal] = []
        position: Position | None = None

        for i, (timestamp, row) in enumerate(bars.iterrows()):
            close = float(row["close"])
            if position is not None:
                exit_price, exit_reason = self._check_exit(row, position)
                if exit_price is not None:
                    pnl, commission = self._close_pnl(position, exit_price)
                    cash += pnl - commission
                    trades.append(
                        {
                            "symbol": strategy.symbol,
                            "strategy": strategy.name,
                            "direction": position.direction,
                            "entry_time": position.entry_time,
                            "exit_time": timestamp,
                            "entry_price": position.entry_price,
                            "exit_price": exit_price,
                            "quantity": position.quantity,
                            "pnl": pnl - commission,
                            "commission": commission,
                            "exit_reason": exit_reason,
                            "hold_bars": i - position.entry_index,
                        }
                    )
                    position = None

            if position is None and i > 0:
                signal = strategy.generate_signal(bars.iloc[: i + 1])
                if signal and signal.direction in {"long", "short"}:
                    signals.append(signal)
                    quantity = self._position_size(cash, signal)
                    if quantity > 0:
                        entry_price = self._apply_slippage(signal.entry_price, signal.direction, is_entry=True)
                        entry_commission = quantity * self.commission_per_share
                        cash -= entry_commission
                        position = Position(
                            direction=signal.direction,
                            quantity=quantity,
                            entry_price=entry_price,
                            entry_time=timestamp,
                            entry_index=i,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                            signal=signal,
                        )

            mark_to_market = cash
            if position is not None:
                mark_to_market += self._unrealized_pnl(position, close)
            equity_values.append(mark_to_market)
            equity_index.append(timestamp)

        if position is not None:
            final_timestamp = bars.index[-1]
            final_price = self._apply_slippage(float(bars.iloc[-1]["close"]), position.direction, is_entry=False)
            pnl, commission = self._close_pnl(position, final_price)
            cash += pnl - commission
            trades.append(
                {
                    "symbol": strategy.symbol,
                    "strategy": strategy.name,
                    "direction": position.direction,
                    "entry_time": position.entry_time,
                    "exit_time": final_timestamp,
                    "entry_price": position.entry_price,
                    "exit_price": final_price,
                    "quantity": position.quantity,
                    "pnl": pnl - commission,
                    "commission": commission,
                    "exit_reason": "end_of_data",
                    "hold_bars": len(bars) - 1 - position.entry_index,
                }
            )
            equity_values[-1] = cash

        equity_curve = pd.Series(equity_values, index=equity_index, name="equity")
        metrics = calculate_trade_metrics(trades, equity_curve, self.initial_capital, self.periods_per_year)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics, signals=signals)

    def _position_size(self, cash: float, signal: TradeSignal) -> int:
        if signal.stop_loss is None:
            return max(0, int((cash * 0.1) // signal.entry_price))
        risk_per_share = abs(signal.entry_price - signal.stop_loss)
        if risk_per_share <= 0:
            return 0
        risk_budget = cash * self.risk_fraction
        return max(0, int(risk_budget // risk_per_share))

    def _check_exit(self, row: pd.Series, position: Position) -> tuple[float | None, str | None]:
        high = float(row["high"])
        low = float(row["low"])
        if position.direction == "long":
            if position.stop_loss is not None and low <= position.stop_loss:
                return self._apply_slippage(position.stop_loss, "long", is_entry=False), "stop_loss"
            if position.take_profit is not None and high >= position.take_profit:
                return self._apply_slippage(position.take_profit, "long", is_entry=False), "take_profit"
        else:
            if position.stop_loss is not None and high >= position.stop_loss:
                return self._apply_slippage(position.stop_loss, "short", is_entry=False), "stop_loss"
            if position.take_profit is not None and low <= position.take_profit:
                return self._apply_slippage(position.take_profit, "short", is_entry=False), "take_profit"
        return None, None

    def _apply_slippage(self, price: float, direction: str, is_entry: bool) -> float:
        bps = self.slippage_bps / 10_000
        sign = 1 if (direction == "long") == is_entry else -1
        return price * (1 + sign * bps)

    def _close_pnl(self, position: Position, exit_price: float) -> tuple[float, float]:
        multiplier = 1 if position.direction == "long" else -1
        pnl = (exit_price - position.entry_price) * position.quantity * multiplier
        commission = position.quantity * self.commission_per_share
        return pnl, commission

    def _unrealized_pnl(self, position: Position, mark_price: float) -> float:
        multiplier = 1 if position.direction == "long" else -1
        return (mark_price - position.entry_price) * position.quantity * multiplier
