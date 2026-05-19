from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    WAIT = "WAIT"
    REDUCE_SIZE = "REDUCE_SIZE"


class OptionDirection(str, Enum):
    CALL = "CALL"
    PUT = "PUT"
    NONE = "NONE"


class NewsSentiment(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class MarketRegime(str, Enum):
    TREND = "TREND"
    CHOP = "CHOP"
    HIGH_VOL = "HIGH_VOL"
    EVENT_RISK = "EVENT_RISK"


class DecisionPayload(BaseModel):
    decision: DecisionType
    direction: OptionDirection = OptionDirection.NONE
    confidence: int = Field(default=0, ge=0, le=100)
    reason_summary: str = ""
    news_sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    market_regime: MarketRegime = MarketRegime.CHOP
    risk_flags: list[str] = Field(default_factory=list)
    size_modifier: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
