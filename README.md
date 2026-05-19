# Trading Bot Systems

This repository contains:

- `ibkr-llm-trading-assistant/` - the original IBKR LLM Trading Assistant MVP.
- A top-level **AI-assisted SPY 0DTE/options scalping system** that uses TradingView for technical signal generation and a FastAPI backend for news, sentiment, regime, risk, replay, dashboard, and paper execution.

The scalping system is designed to **filter and score trade opportunities in real time**. It does not pretend Pine Script can call an LLM, pull news, or execute options directly.

## Components

```text
/pine/spy_0dte_scalper.pine       TradingView Pine Script v5 strategy
/backend/main.py                  FastAPI app
/backend/routes/                  Webhook and dashboard routes
/backend/services/                Decision, risk, options, replay, analytics services
/backend/models/                  SQLAlchemy persistence models
/backend/schemas/                 Pydantic schemas
/ai/                              News provider, sentiment, and mock LLM decision layer
/execution/                       Paper executor and future broker adapter stubs
/dashboard/                       Lightweight HTML dashboard renderer
/tests/                           Unit and integration tests
/docs/                            Alert templates and architecture notes
```

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Open:

- API health: <http://localhost:8000/health>
- Dashboard: <http://localhost:8000/dashboard>
- OpenAPI docs: <http://localhost:8000/docs>

## Docker run

```bash
cp .env.example .env
docker compose up --build
```

The app listens on <http://localhost:8000>. SQLite data is stored in `./data`.

## TradingView setup

1. Open TradingView on `SPY`.
2. Add `pine/spy_0dte_scalper.pine` as a Pine Script v5 strategy.
3. Configure strategy inputs:
   - EMA 9 / EMA 21 trend alignment
   - VWAP, RSI, MACD, ATR stop/target
   - Opening range breakout toggle
   - Morning session `09:35-11:30` ET
   - Optional afternoon session `13:30-15:30` ET
   - Lunch block `11:30-13:30` ET
   - Entry mode: `Aggressive`, `Standard`, or `Conservative`
4. Create an alert from the strategy.
5. Enable **Webhook URL** and point it to:

   ```text
   https://your-public-host/webhook/tradingview
   ```

6. For strategy order-fill alerts, use this message:

   ```text
   {{strategy.order.alert_message}}
   ```

   The strategy constructs valid JSON dynamically for entries and exits.

7. If you use a shared secret, set `WEBHOOK_SECRET` in `.env` and include `"secret": "..."` in custom alert JSON.

## Example webhook JSON

```json
{
  "ticker": "SPY",
  "time": "2026-05-19T14:00:00Z",
  "price": 525.25,
  "interval": "1",
  "action": "BUY_CALL_SETUP",
  "market_position": "flat",
  "setup": "SPY_0DTE_SCALP",
  "bias": "bullish",
  "rsi": 58.2,
  "ema_fast": 526.0,
  "ema_slow": 524.1,
  "macd_state": "bullish",
  "volume_state": "spike",
  "vwap_state": "above",
  "opening_range_breakout": true,
  "atr": 0.9
}
```

## Webhook response

The backend returns structured trade filtering output:

```json
{
  "response": {
    "decision": "APPROVE",
    "direction": "CALL",
    "confidence": 0.7,
    "reason_summary": "Bullish technical setup maps to CALL...",
    "news_sentiment": "BULLISH",
    "market_regime": "TREND",
    "risk_flags": [],
    "rejection_reasons": [],
    "size_modifier": 1.0
  }
}
```

Valid decisions are `APPROVE`, `REJECT`, `REDUCE_SIZE`, and `WAIT`.

## Risk presets

Set `RISK_PRESET` to:

- `conservative`
- `standard`
- `aggressive`

The risk engine enforces max daily loss, max trades per day, max consecutive losses, cooldown concepts, stale and duplicate alert rejection, session windows, max capital at risk, max exposure, option spread width, option volume/open-interest filters when quote data is available, and a hard kill switch.

## Replay

Save one webhook payload per line and compare filtering modes:

```bash
python -m backend.replay docs/sample_webhook_payloads.jsonl --mode pine
python -m backend.replay docs/sample_webhook_payloads.jsonl --mode pine-ai
python -m backend.replay docs/sample_webhook_payloads.jsonl --mode full
```

Modes:

- `pine` - base technical payload processing
- `pine-ai` - Pine + AI/news filtering
- `full` - Pine + AI/news + risk engine

## Tests

```bash
pytest
```

## Live broker execution

Default mode is paper trading. `execution/tradier_adapter.py` and `execution/ibkr_adapter.py` are intentional stubs. Before live trading, implement authenticated order routing, quote retrieval, spread checks from real options data, broker-side kill switches, and operational monitoring. Then explicitly set:

```env
ENABLE_BROKER_EXECUTION=true
PAPER_TRADING=false
```

## Known limitations

- TradingView webhooks are alert/event driven; they are not a broker or real-time options chain provider.
- Pine Script cannot call LLMs, news APIs, or broker APIs directly.
- Mock news and mock AI are deterministic defaults for development and testing.
- Option quotes, Greeks, open interest, and volume require a real broker/data provider before live execution.
- 0DTE spreads, liquidity, halts, latency, and market-event gaps can invalidate simulated fills.
- This is not investment advice and does not predict future prices with certainty.
