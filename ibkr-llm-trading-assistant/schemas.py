"""Shared Pydantic schemas for signals, orders, and LLM responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AssetClass(str, Enum):
    STK = "STK"
    ETF = "ETF"
    OPT = "OPT"
    FUT = "FUT"
    CASH = "CASH"  # Forex


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Timeframe(str, Enum):
    M1 = "1 min"
    M5 = "5 mins"
    M15 = "15 mins"
    H1 = "1 hour"
    D1 = "1 day"


class TradeSignal(BaseModel):
    """Structured trade signal from strategy or model."""

    symbol: str
    asset_class: AssetClass = AssetClass.STK
    timeframe: Timeframe = Timeframe.M5
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    exchange: str = "SMART"
    currency: str = "USD"
    quantity: Optional[float] = None
    strategy_name: str = ""
    model_score: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def reward_to_risk(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        if risk <= 0:
            return 0.0
        return reward / risk

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v


class LLMTradeReview(BaseModel):
    """Structured LLM analysis output — never executes trades."""

    trade_allowed: bool = False
    setup_quality: float = Field(ge=0.0, le=1.0, default=0.0)
    market_regime: str = "unknown"
    reasoning: str = ""
    risks: list[str] = Field(default_factory=list)
    suggested_adjustments: dict[str, float] = Field(default_factory=dict)
    suggested_backtests: list[str] = Field(default_factory=list)
    strategy_weaknesses: list[str] = Field(default_factory=list)


class RiskCheckResult(BaseModel):
    """Result of deterministic risk validation."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    adjusted_quantity: Optional[float] = None


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class BacktestTrade(BaseModel):
    """Single trade from backtest."""

    symbol: str
    direction: Direction
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    commission: float
    slippage: float
    strategy_name: str
    exit_reason: str = ""


class BacktestResult(BaseModel):
    """Aggregated backtest metrics."""

    strategy_name: str
    symbol: str
    timeframe: str
    total_return: float
    cagr: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    expectancy: float
    sharpe_ratio: float
    sortino_ratio: float
    num_trades: int
    avg_hold_time_hours: float
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[float] = Field(default_factory=list)


class StrategyRanking(BaseModel):
    """Strategy performance for self-improvement loop."""

    strategy_name: str
    symbol: str
    asset_class: str
    timeframe: str
    total_trades: int
    win_rate: float
    expectancy: float
    sharpe_ratio: float
    rank_score: float
    promoted: bool = False
    requires_human_approval: bool = True
