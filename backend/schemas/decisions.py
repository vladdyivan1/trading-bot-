from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    WAIT = "WAIT"
    REDUCE_SIZE = "REDUCE_SIZE"


class Direction(str, Enum):
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


class AIDecision(BaseModel):
    decision: DecisionAction
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    reason_summary: str = ""
    news_sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    market_regime: MarketRegime = MarketRegime.TREND
    risk_flags: List[str] = Field(default_factory=list)
    size_modifier: float = Field(default=1.0, ge=0.0, le=2.0)
    headlines_used: int = 0
    technical_only: bool = False
