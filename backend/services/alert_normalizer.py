"""Normalize and validate TradingView alert payloads."""

import hashlib
import json
from datetime import datetime
from typing import Any

from backend.schemas.alerts import TradingViewAlert


def generate_alert_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_alert(raw: dict[str, Any]) -> TradingViewAlert:
    """Map raw webhook JSON to typed alert."""
    data = {k: v for k, v in raw.items() if v is not None}
    ticker = str(data.get("ticker", "SPY")).upper()
    if ticker in ("SPY", "AMEX:SPY", "NYSE:SPY"):
        data["ticker"] = "SPY"
    return TradingViewAlert.model_validate(data)


def parse_alert_time(time_str: str | None) -> datetime | None:
    if not time_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(time_str.replace("Z", "+0000"), fmt)
        except ValueError:
            continue
    return None
