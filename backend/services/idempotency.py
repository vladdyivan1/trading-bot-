from __future__ import annotations

import hashlib

from backend.schemas.tradingview import TradingViewAlert


def idempotency_key(alert: TradingViewAlert) -> str:
    payload = f"{alert.normalized_symbol()}|{alert.event_time_utc().isoformat()}|{alert.action}|{alert.price:.4f}|{alert.interval}|{alert.bias}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
