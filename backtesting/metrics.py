"""Backtest performance metric calculations."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def calculate_drawdown(equity_curve: pd.Series) -> pd.Series:
    rolling_max = equity_curve.cummax()
    return (equity_curve - rolling_max) / rolling_max.replace(0, np.nan)


def summarize_backtest_metrics(trades: pd.DataFrame, equity_curve: pd.Series, annualization: int = 252) -> dict:
    if equity_curve.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "expectancy": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "num_trades": 0,
            "average_hold_time_hours": 0.0,
        }

    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0)
    duration_days = max(1, (equity_curve.index[-1] - equity_curve.index[0]).days)
    cagr = float((1 + total_return) ** (365 / duration_days) - 1)

    num_trades = int(len(trades))
    if num_trades == 0:
        wins = pd.Series(dtype=float)
        losses = pd.Series(dtype=float)
        expectancy = 0.0
        win_rate = 0.0
        profit_factor = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        avg_hold_hours = 0.0
    else:
        pnl = trades["pnl"].astype(float)
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        win_rate = float(len(wins) / num_trades)
        profit_factor = float(abs(wins.sum() / losses.sum())) if len(losses) > 0 else float("inf")
        avg_win = float(wins.mean()) if len(wins) else 0.0
        avg_loss = float(losses.mean()) if len(losses) else 0.0
        expectancy = float(pnl.mean())
        hold_times = trades["hold_time"].tolist()
        hold_hours = [ht.total_seconds() / 3600 for ht in hold_times if isinstance(ht, timedelta)]
        avg_hold_hours = float(np.mean(hold_hours)) if hold_hours else 0.0

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        sharpe = 0.0
        sortino = 0.0
    else:
        sharpe = float((returns.mean() / returns.std()) * np.sqrt(annualization)) if returns.std() != 0 else 0.0
        downside = returns[returns < 0]
        sortino = float((returns.mean() / downside.std()) * np.sqrt(annualization)) if len(downside) > 1 and downside.std() != 0 else 0.0

    max_drawdown = float(calculate_drawdown(equity_curve).min())

    return {
        "total_return": total_return,
        "cagr": cagr,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "average_win": avg_win,
        "average_loss": avg_loss,
        "expectancy": expectancy,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "num_trades": num_trades,
        "average_hold_time_hours": avg_hold_hours,
    }
