"""TradingView webhook payload validation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None or value == "":
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        number = int(text)
        if number > 10_000_000_000:
            number = number // 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class TradingViewAlert(BaseModel):
    """Normalized SPY scalping alert from TradingView strategy alerts."""

    ticker: str
    time: datetime
    price: float
    interval: str = "1"
    action: str
    market_position: str = "flat"
    setup: str = "SPY_0DTE_SCALP"
    bias: Literal["bullish", "bearish", "neutral"]
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    macd_state: str | None = None
    volume_state: str | None = None
    vwap_state: str | None = None
    atr: float | None = None
    opening_range_breakout: bool | None = None
    secret: str | None = Field(default=None, exclude=True)
    raw_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: Any) -> str:
        ticker = str(value or "").upper().split(":")[-1].strip()
        if not ticker:
            raise ValueError("ticker is required")
        return ticker

    @field_validator("time", mode="before")
    @classmethod
    def parse_alert_time(cls, value: Any) -> datetime:
        return _parse_time(value)

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, value: Any) -> float:
        parsed = _coerce_float(value)
        if parsed is None or parsed <= 0:
            raise ValueError("price must be positive")
        return parsed

    @field_validator("rsi", "ema_fast", "ema_slow", "atr", mode="before")
    @classmethod
    def parse_optional_float(cls, value: Any) -> float | None:
        return _coerce_float(value)

    @field_validator("bias", mode="before")
    @classmethod
    def normalize_bias(cls, value: Any) -> str:
        text = str(value or "").lower()
        if "bull" in text or text == "call":
            return "bullish"
        if "bear" in text or text == "put":
            return "bearish"
        return "neutral"

    @field_validator("action", "market_position", "setup", "interval", mode="before")
    @classmethod
    def stringify(cls, value: Any) -> str:
        return str(value or "").strip()

    @model_validator(mode="before")
    @classmethod
    def keep_raw_payload(cls, values: Any) -> Any:
        if isinstance(values, dict):
            copied = dict(values)
            copied["raw_payload"] = dict(values)
            return copied
        return values

    @property
    def direction(self) -> Literal["CALL", "PUT", "NONE"]:
        if self.bias == "bullish":
            return "CALL"
        if self.bias == "bearish":
            return "PUT"
        return "NONE"

    def idempotency_key(self) -> str:
        parts = [
            self.ticker,
            self.time.isoformat(),
            f"{self.price:.4f}",
            self.interval,
            self.action.lower(),
            self.bias,
            self.setup,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
