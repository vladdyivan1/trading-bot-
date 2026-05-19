import json
from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent.parent / "docs" / "sample_webhook.json"


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_bullish_alert(client):
    payload = json.loads(SAMPLE.read_text())
  # Use unique time to avoid duplicate dedup from prior runs
    payload["time"] = "2026-05-19T10:25:00-04:00"
    payload["bias"] = "bullish"
    payload["action"] = "buy"
    r = await client.post("/webhook/tradingview", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] in ("APPROVE", "REJECT", "WAIT", "REDUCE_SIZE")
    assert data["direction"] in ("CALL", "PUT", "NONE")


@pytest.mark.asyncio
async def test_webhook_invalid_json(client):
    r = await client.post("/webhook/tradingview", content=b"not-json")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_analytics_endpoints(client):
    await client.post(
        "/webhook/tradingview",
        json={
            "ticker": "SPY",
            "time": "2026-05-19T11:00:00-04:00",
            "price": "503.0",
            "bias": "bearish",
            "action": "sell",
        },
    )
    r = await client.get("/api/analytics/summary")
    assert r.status_code == 200
    assert "win_rate" in r.json()
