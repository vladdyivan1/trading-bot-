"""Pydantic schemas for signals, LLM output, and trade validation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AssetClass(str, Enum):
    STK = "STK"
    ETF = "ETF"
    OPT = "OPT"
    FUT = "FUT"
    CASH = "CASH"


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class TradeSignal(BaseModel):
    """Structured trade signal from strategies or ML models."""

    symbol: str
    asset_class: str = "STK"
    timeframe: str = "5 mins"
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    strategy_name: str = ""
    timestamp: datetime | None = None

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: Any) -> Direction:
        if isinstance(v, Direction):
            return v
        return Direction(str(v).lower())

    @property
    def reward_to_risk(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        if risk <= 0:
            return 0.0
        return reward / risk

    def model_dump_json_safe(self) -> dict[str, Any]:
        data = self.model_dump()
        if self.timestamp:
            data["timestamp"] = self.timestamp.isoformat()
        data["direction"] = self.direction.value
        return data


class LLMRecommendation(BaseModel):
    """Structured LLM analysis output — never executes trades directly."""

    trade_allowed: bool
    setup_quality: float = Field(ge=0.0, le=1.0)
    market_regime: str = "unknown"
    reasoning: str = ""
    risks: list[str] = Field(default_factory=list)
    suggested_adjustments: dict[str, float] = Field(default_factory=dict)


class RiskCheckResult(BaseModel):
    """Result of deterministic risk manager validation."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    adjusted_quantity: int | None = None


class BacktestMetrics(BaseModel):
    """Performance metrics from a backtest run."""

    total_return: float = 0.0
    cagr: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    num_trades: int = 0
    avg_hold_bars: float = 0.0
