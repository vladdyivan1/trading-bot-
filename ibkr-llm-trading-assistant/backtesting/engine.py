"""Deterministic event-driven backtesting engine."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pandas as pd
from loguru import logger

from backtesting.metrics import compute_metrics
from config.settings import get_settings
from schemas import BacktestResult, BacktestTrade, Direction
from strategies.base_strategy import BaseStrategy


class BacktestEngine:
    """Bar-by-bar backtest with stops, targets, commission, and slippage."""

    def __init__(
        self,
        initial_capital: Optional[float] = None,
        commission_per_share: Optional[float] = None,
        slippage_pct: Optional[float] = None,
    ):
        settings = get_settings()
        self.initial_capital = initial_capital or settings.initial_capital
        self.commission = commission_per_share or settings.default_commission_per_share
        self.slippage_pct = slippage_pct or settings.default_slippage_pct

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        position_size_pct: float = 0.1,
    ) -> BacktestResult:
        """Run backtest on historical OHLCV data."""
        if len(df) < 50:
            logger.warning("Insufficient data for backtest")
            return compute_metrics(
                [], [self.initial_capital], self.initial_capital,
                strategy.name, strategy.symbol, str(strategy.timeframe.value),
            )

        enriched = strategy.calculate_indicators(df.copy())
        capital = self.initial_capital
        equity_curve = [capital]
        trades: List[BacktestTrade] = []
        position: Optional[dict] = None

        for i in range(50, len(enriched)):
            window = enriched.iloc[: i + 1]
            bar = enriched.iloc[i]
            bar_time = bar.name if isinstance(bar.name, datetime) else datetime.utcnow()

            if position:
                exit_price, exit_reason = self._check_exit(position, bar)
                if exit_price is not None:
                    pnl = self._close_position(position, exit_price, capital, position_size_pct)
                    commission = position["quantity"] * self.commission * 2
                    slippage = position["quantity"] * position["entry"] * self.slippage_pct
                    net_pnl = pnl - commission - slippage
                    capital += net_pnl
                    trades.append(
                        BacktestTrade(
                            symbol=strategy.symbol,
                            direction=position["direction"],
                            entry_time=position["entry_time"],
                            exit_time=bar_time,
                            entry_price=position["entry"],
                            exit_price=exit_price,
                            quantity=position["quantity"],
                            pnl=net_pnl,
                            commission=commission,
                            slippage=slippage,
                            strategy_name=strategy.name,
                            exit_reason=exit_reason,
                        )
                    )
                    position = None

            if position is None:
                signal = strategy.generate_signal(window)
                if signal and signal.direction != Direction.FLAT:
                    risk_per_share = abs(signal.entry_price - signal.stop_loss)
                    if risk_per_share <= 0:
                        continue
                    risk_amount = capital * position_size_pct
                    quantity = max(1, int(risk_amount / risk_per_share))
                    entry = signal.entry_price * (
                        1 + self.slippage_pct
                        if signal.direction == Direction.LONG
                        else 1 - self.slippage_pct
                    )
                    position = {
                        "direction": signal.direction,
                        "entry": entry,
                        "stop": signal.stop_loss,
                        "target": signal.take_profit,
                        "quantity": quantity,
                        "entry_time": bar_time,
                    }

            equity_curve.append(capital)

        if position:
            last = enriched.iloc[-1]
            exit_price = float(last["close"])
            pnl = self._close_position(position, exit_price, capital, position_size_pct)
            capital += pnl
            trades.append(
                BacktestTrade(
                    symbol=strategy.symbol,
                    direction=position["direction"],
                    entry_time=position["entry_time"],
                    exit_time=last.name if isinstance(last.name, datetime) else datetime.utcnow(),
                    entry_price=position["entry"],
                    exit_price=exit_price,
                    quantity=position["quantity"],
                    pnl=pnl,
                    commission=0.0,
                    slippage=0.0,
                    strategy_name=strategy.name,
                    exit_reason="end_of_data",
                )
            )
            equity_curve.append(capital)

        return compute_metrics(
            trades,
            equity_curve,
            self.initial_capital,
            strategy.name,
            strategy.symbol,
            str(strategy.timeframe.value),
        )

    def _check_exit(self, position: dict, bar: pd.Series) -> tuple[Optional[float], str]:
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if position["direction"] == Direction.LONG:
            if low <= position["stop"]:
                return position["stop"], "stop_loss"
            if high >= position["target"]:
                return position["target"], "take_profit"
        else:
            if high >= position["stop"]:
                return position["stop"], "stop_loss"
            if low <= position["target"]:
                return position["target"], "take_profit"
        return None, ""

    def _close_position(
        self, position: dict, exit_price: float, capital: float, size_pct: float
    ) -> float:
        qty = position["quantity"]
        if position["direction"] == Direction.LONG:
            return (exit_price - position["entry"]) * qty
        return (position["entry"] - exit_price) * qty

    def compare_strategies(
        self,
        strategies: List[BaseStrategy],
        df: pd.DataFrame,
    ) -> List[BacktestResult]:
        return [self.run(s, df) for s in strategies]
