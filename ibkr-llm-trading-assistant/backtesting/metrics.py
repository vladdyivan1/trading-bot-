"""Backtest performance metrics."""

from __future__ import annotations

from datetime import datetime
from typing import List

import numpy as np
import pandas as pd

from schemas import BacktestResult, BacktestTrade, Direction


def compute_metrics(
    trades: List[BacktestTrade],
    equity_curve: List[float],
    initial_capital: float,
    strategy_name: str,
    symbol: str,
    timeframe: str,
) -> BacktestResult:
    """Calculate all backtest statistics."""
    if not trades:
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            total_return=0.0,
            cagr=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            expectancy=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            num_trades=0,
            avg_hold_time_hours=0.0,
            trades=[],
            equity_curve=equity_curve,
        )

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_return = (equity_curve[-1] - initial_capital) / initial_capital * 100

    days = max(
        1,
        (trades[-1].exit_time - trades[0].entry_time).days,
    )
    years = days / 365.25
    cagr = (
        ((equity_curve[-1] / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    )

    win_rate = len(wins) / len(pnls) * 100 if pnls else 0.0
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-10
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    max_dd = _max_drawdown(equity_curve)
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    expectancy = np.mean(pnls) if pnls else 0.0

    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = _sharpe_ratio(returns)
    sortino = _sortino_ratio(returns)

    hold_times = [
        (t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades
    ]
    avg_hold = float(np.mean(hold_times)) if hold_times else 0.0

    return BacktestResult(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        total_return=float(total_return),
        cagr=float(cagr),
        win_rate=float(win_rate),
        profit_factor=float(profit_factor),
        max_drawdown=float(max_dd),
        avg_win=float(avg_win),
        avg_loss=float(avg_loss),
        expectancy=float(expectancy),
        sharpe_ratio=float(sharpe),
        sortino_ratio=float(sortino),
        num_trades=len(trades),
        avg_hold_time_hours=avg_hold,
        trades=trades,
        equity_curve=equity_curve,
    )


def _max_drawdown(equity: List[float]) -> float:
    if len(equity) < 2:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        dd = (peak - v) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def _sharpe_ratio(returns: pd.Series, risk_free: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2 or returns.std() < 1e-10:
        return 0.0
    excess = returns.mean() - risk_free / periods
    return float(excess / returns.std() * np.sqrt(periods))


def _sortino_ratio(returns: pd.Series, risk_free: float = 0.0, periods: int = 252) -> float:
    downside = returns[returns < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    excess = returns.mean() - risk_free / periods
    return float(excess / downside.std() * np.sqrt(periods))
