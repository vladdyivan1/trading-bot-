"""Decision response schemas returned by the webhook pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DecisionValue = Literal["APPROVE", "REJECT", "REDUCE_SIZE", "WAIT"]
DirectionValue = Literal["CALL", "PUT", "NONE"]
SentimentValue = Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
RegimeValue = Literal["TREND", "CHOP", "HIGH_VOL", "EVENT_RISK"]


class DecisionResponse(BaseModel):
    decision: DecisionValue
    direction: DirectionValue
    confidence: float = Field(ge=0.0, le=1.0)
    reason_summary: str
    news_sentiment: SentimentValue
    market_regime: RegimeValue
    risk_flags: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    size_modifier: float = Field(ge=0.0, le=1.0)


class ExecutionResult(BaseModel):
    status: str
    order_id: str | None = None
    symbol: str | None = None
    quantity: int = 0
    fill_price: float = 0.0
    message: str = ""


class DecisionEnvelope(BaseModel):
    alert_id: int
    decision_id: int
    received_at: datetime
    response: DecisionResponse
    execution: ExecutionResult | None = None
