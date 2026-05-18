"""Backtest performance metrics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def max_drawdown(equity_curve: pd.Series) -> float:
    """Return max drawdown as a negative percentage."""

    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdowns = equity_curve / running_max - 1
    return float(drawdowns.min())


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.empty or returns.std(ddof=0) == 0:
        return 0.0
    return float((returns.mean() / returns.std(ddof=0)) * math.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    downside = returns[returns < 0]
    if returns.empty or downside.std(ddof=0) == 0:
        return 0.0
    return float((returns.mean() / downside.std(ddof=0)) * math.sqrt(periods_per_year))


def calculate_trade_metrics(
    trades: list[dict[str, Any]],
    equity_curve: pd.Series,
    initial_capital: float,
    periods_per_year: int = 252,
) -> dict[str, float]:
    """Calculate standard trading performance metrics."""

    final_equity = float(equity_curve.iloc[-1]) if not equity_curve.empty else initial_capital
    total_return = final_equity / initial_capital - 1
    returns = equity_curve.pct_change().dropna() if not equity_curve.empty else pd.Series(dtype=float)

    years = max(len(equity_curve) / periods_per_year, 1 / periods_per_year)
    cagr = (final_equity / initial_capital) ** (1 / years) - 1 if initial_capital > 0 else 0.0

    pnl = np.array([float(t.get("pnl", 0.0)) for t in trades], dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = abs(float(losses.sum())) if losses.size else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    win_rate = float((pnl > 0).mean()) if pnl.size else 0.0
    avg_win = float(wins.mean()) if wins.size else 0.0
    avg_loss = float(losses.mean()) if losses.size else 0.0
    expectancy = float(pnl.mean()) if pnl.size else 0.0
    hold_times = [float(t.get("hold_bars", 0.0)) for t in trades]

    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "win_rate": win_rate,
        "profit_factor": float(profit_factor),
        "max_drawdown": max_drawdown(equity_curve),
        "average_win": avg_win,
        "average_loss": avg_loss,
        "expectancy": expectancy,
        "sharpe_ratio": sharpe_ratio(returns, periods_per_year),
        "sortino_ratio": sortino_ratio(returns, periods_per_year),
        "number_of_trades": float(len(trades)),
        "average_hold_time": float(np.mean(hold_times)) if hold_times else 0.0,
    }
