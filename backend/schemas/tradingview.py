from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TradingViewAlert(BaseModel):
    ticker: str = Field(min_length=1)
    time: datetime
    price: float = Field(gt=0)
    interval: str = Field(min_length=1)
    action: str = Field(min_length=1)
    market_position: str | None = None
    setup: str = "SPY_0DTE_SCALP"
    bias: str = "neutral"
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    macd_state: str | None = None
    volume_state: str | None = None
    vwap_state: str | None = None
    atr: float | None = None
    opening_range_breakout: bool | None = None
    payload_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def coerce_numeric_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        for key in ("price", "rsi", "ema_fast", "ema_slow", "atr"):
            value = values.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped == "":
                    values[key] = None
                    continue
                try:
                    values[key] = float(stripped)
                except ValueError:
                    values[key] = None
        return values

    def normalized_symbol(self) -> str:
        return self.ticker.upper().replace("NASDAQ:", "").replace("NYSE:", "")

    def event_time_utc(self) -> datetime:
        if self.time.tzinfo is None:
            return self.time.replace(tzinfo=UTC)
        return self.time.astimezone(UTC)
