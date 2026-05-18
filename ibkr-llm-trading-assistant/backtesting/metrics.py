"""Backtest performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from schemas import BacktestMetrics


def compute_metrics(
    trades: pd.DataFrame,
    equity_curve: pd.Series,
    bars_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> BacktestMetrics:
    """Calculate performance statistics from trades and equity curve."""
    if trades.empty:
        return BacktestMetrics()

    pnl = trades["pnl"].dropna()
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    num_trades = len(pnl)

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) if len(equity_curve) > 1 else 0.0
    years = max(len(equity_curve) / bars_per_year, 1 / bars_per_year)
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    win_rate = len(wins) / num_trades if num_trades else 0.0
    gross_profit = wins.sum() if len(wins) else 0.0
    gross_loss = abs(losses.sum()) if len(losses) else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max.replace(0, np.nan)
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    expectancy = float(pnl.mean()) if num_trades else 0.0

    returns = equity_curve.pct_change().dropna()
    excess = returns - risk_free_rate / bars_per_year
    sharpe = (
        float(excess.mean() / excess.std() * np.sqrt(bars_per_year))
        if len(excess) > 1 and excess.std() > 0
        else 0.0
    )
    downside = returns[returns < 0]
    sortino = (
        float(returns.mean() / downside.std() * np.sqrt(bars_per_year))
        if len(downside) > 1 and downside.std() > 0
        else 0.0
    )

    hold_bars = trades["hold_bars"].mean() if "hold_bars" in trades.columns else 0.0

    return BacktestMetrics(
        total_return=float(total_return),
        cagr=float(cagr),
        win_rate=float(win_rate),
        profit_factor=float(profit_factor) if profit_factor != float("inf") else 999.0,
        max_drawdown=float(max_drawdown),
        avg_win=avg_win,
        avg_loss=avg_loss,
        expectancy=expectancy,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        num_trades=num_trades,
        avg_hold_bars=float(hold_bars) if pd.notna(hold_bars) else 0.0,
    )
