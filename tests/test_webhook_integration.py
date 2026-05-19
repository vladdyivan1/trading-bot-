import uuid

import pytest


def _payload(recent_time: str) -> dict:
    return {
        "ticker": "SPY",
        "time": recent_time,
        "price": str(585 + uuid.uuid4().int % 1000 / 1000),
        "interval": "1",
        "action": "buy",
        "market_position": "long",
        "setup": "SPY_0DTE_SCALP",
        "bias": "bullish",
        "rsi": "58.2",
        "ema_fast": "585.10",
        "ema_slow": "584.55",
        "macd_state": "bullish",
        "volume_state": "spike",
        "vwap_state": "above",
        "atr": "1.25",
        "secret": "test-secret",
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_processes_bullish(client, recent_time):
    r = client.post("/webhook/tradingview", json=_payload(recent_time))
    assert r.status_code == 200
    data = r.json()
    assert data["alert_id"]
    assert data["status"] in ("approved", "rejected", "wait")


def test_webhook_rejects_bad_secret(client, recent_time):
    p = _payload(recent_time)
    p["secret"] = "wrong"
    r = client.post("/webhook/tradingview", json=p)
    assert r.status_code == 200
    assert r.json().get("rejection_reason") == "INVALID_WEBHOOK_SECRET"


def test_idempotent_duplicate(client, recent_time):
    payload = _payload(recent_time)
    client.post("/webhook/tradingview", json=payload)
    r2 = client.post("/webhook/tradingview", json=payload)
    assert r2.json().get("status") == "duplicate" or r2.json().get("rejection_reason")
