from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


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
    entry_mode: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("price", "rsi", "ema_fast", "ema_slow", "atr", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @property
    def is_bullish(self) -> bool:
        return (self.bias or "").lower() in ("bullish", "bull") or (
            self.action or ""
        ).lower() in ("buy", "long")

    @property
    def is_bearish(self) -> bool:
        return (self.bias or "").lower() in ("bearish", "bear") or (
            self.action or ""
        ).lower() in ("sell", "short")

    def parsed_time(self) -> Optional[datetime]:
        if not self.time:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.fromisoformat(self.time.replace("Z", "+00:00"))
            except ValueError:
                continue
        return None


class WebhookResponse(BaseModel):
    status: str
    decision: str
    direction: str
    confidence: float
    reason_summary: str
    execution_id: Optional[str] = None
    rejection_reasons: list[str] = Field(default_factory=list)
