from typing import Any, Optional

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_alerts: int = 0
    approved: int = 0
    rejected: int = 0
    wait: int = 0
    reduce_size: int = 0
    open_positions: int = 0
    closed_positions: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    rejection_reasons: dict[str, int] = {}
    sentiment_breakdown: dict[str, int] = {}
    regime_breakdown: dict[str, int] = {}
    time_of_day_performance: dict[str, Any] = {}
    recent_alerts: list[dict] = []
    recent_decisions: list[dict] = []
