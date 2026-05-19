from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.main import app


def test_webhook_route_processes_payload() -> None:
    client = TestClient(app)
    payload = {
        "ticker": "SPY",
        "time": datetime.now(UTC).isoformat(),
        "price": 525.35,
        "interval": "1",
        "action": "BUY_CALL",
        "market_position": "flat",
        "setup": "SPY_0DTE_SCALP",
        "bias": "bullish",
        "rsi": 58.4,
        "ema_fast": 525.1,
        "ema_slow": 524.7,
        "macd_state": "bullish_trend",
        "volume_state": "spike",
        "vwap_state": "above_vwap",
        "atr": 1.15,
    }
    response = client.post("/webhook/tradingview", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"] in {"APPROVE", "REJECT", "WAIT", "REDUCE_SIZE"}
    assert "reason_summary" in body["decision"]
