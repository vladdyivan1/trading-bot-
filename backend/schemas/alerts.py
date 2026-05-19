"""Pydantic schemas for webhook and AI decisions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    WAIT = "WAIT"
    REDUCE_SIZE = "REDUCE_SIZE"


class Direction(str, Enum):
    CALL = "CALL"
    PUT = "PUT"
    NONE = "NONE"


class Sentiment(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class MarketRegime(str, Enum):
    TREND = "TREND"
    CHOP = "CHOP"
    HIGH_VOL = "HIGH_VOL"
    EVENT_RISK = "EVENT_RISK"


class TradingViewAlert(BaseModel):
    """Normalized TradingView webhook payload."""

    ticker: str = "SPY"
    time: Optional[str] = None
    price: Optional[float] = None
    interval: Optional[str] = None
    action: Optional[str] = None
    market_position: Optional[str] = None
    setup: str = "SPY_0DTE_SCALP"
    bias: Optional[str] = None
    rsi: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    macd_state: Optional[str] = None
    volume_state: Optional[str] = None
    vwap_state: Optional[str] = None
    atr: Optional[float] = None
    secret: Optional[str] = None

    model_config = {"extra": "allow"}

    @field_validator("price", "rsi", "ema_fast", "ema_slow", "atr", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


class AIDecisionResponse(BaseModel):
    decision: Decision
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    reason_summary: str
    news_sentiment: Sentiment
    market_regime: MarketRegime
    risk_flags: list[str] = Field(default_factory=list)
    size_modifier: float = Field(default=1.0, ge=0.0, le=1.0)


class WebhookResponse(BaseModel):
    status: str
    alert_id: str
    decision: Optional[AIDecisionResponse] = None
    execution: Optional[dict] = None
    rejection_reason: Optional[str] = None
    latency_ms: float = 0.0
    received_at: datetime = Field(default_factory=datetime.utcnow)
