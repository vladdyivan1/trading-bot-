# AI-Assisted SPY 0DTE/1DTE Scalping System (TradingView + Webhook Backend)

This repository now includes a production-style scaffold for **SPY options scalping** where:

- **TradingView Pine Script** generates technical signals and JSON alerts.
- **FastAPI backend** receives webhook alerts and validates/idempotently processes them.
- **AI/news + regime + risk engine** filters and scores trade opportunities in real time (probabilistic, not certainty claims).
- **Execution layer** defaults to paper trading and supports future broker adapters.
- **Dashboard** shows decisions, positions, PnL, rejection analytics, sentiment heatmap, and regime/time-of-day metrics.

> Pine Script does **not** call external LLMs/news APIs directly. It only emits technical alert payloads.

---

## Project Structure

```text
/pine
  spy_0dte_scalper.pine
/backend
  main.py
  replay.py
  /routes
  /services
  /models
  /schemas
/ai
  sentiment_engine.py
  llm_decision.py
  news_providers.py
/execution
  paper_executor.py
  broker_base.py
  tradier_adapter.py
  ibkr_adapter.py
/dashboard
  index.html
/tests
/docs
.env.example
docker-compose.yml
Dockerfile
requirements.txt
```

---

## Core Capabilities

### 1) TradingView Pine Strategy (`pine/spy_0dte_scalper.pine`)
- EMA 9 / EMA 21 alignment
- VWAP filter
- RSI thresholds (aggressive/standard/conservative presets)
- MACD confirmation
- ATR stop/target logic
- Opening range breakout option
- Volume spike filter
- Session windows (default 9:35-11:30 ET and optional 1:30-3:30 ET)
- Lunch no-trade filter
- Long call bias for bullish setup and long put bias for bearish setup
- Alert-ready JSON with TradingView placeholders and dynamic indicator values

### 2) Webhook backend (`POST /webhook/tradingview`)
- FastAPI + Pydantic validation
- Idempotency key + duplicate window checks
- Stale alert rejection
- Symbol/action normalization
- News/sentiment/regime enrichment
- AI decision payload:
  - `APPROVE`, `REJECT`, `WAIT`, `REDUCE_SIZE`
- Risk overlay (max loss, max trades/day, cooldown, event blackout, session controls)
- Paper execution simulation for options contract selection

### 3) AI / News Layer
- Mock provider for offline development
- Optional News API provider (`NEWS_API_URL`, `NEWS_API_KEY`)
- Sentiment classification: bullish/bearish/neutral/mixed
- Event risk detection: Fed/CPI/jobs/FOMC/Powell-style flags
- Probabilistic decision scoring (confidence + reason summary)

### 4) Execution Layer
- Paper adapter with options-aware selection logic:
  - nearest expiration (0DTE default, 1DTE fallback)
  - delta band filters
  - min open interest / volume filters
  - spread-width guard
- Broker adapter stubs:
  - Tradier
  - IBKR

### 5) Dashboard + Analytics
- `/dashboard` UI
- Recent alerts + decisions
- Open/closed positions
- PnL, win rate, max drawdown
- Time-of-day performance
- Rejection reason analytics
- News sentiment heatmap
- Regime analytics

---

## Local Run Instructions

```bash
# from repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# run API
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/dashboard`

Run tests:
```bash
pytest -q tests
```

---

## Docker Run Instructions

```bash
cp .env.example .env
docker compose up --build
```

Services:
- Backend: `http://localhost:8000`
- Dashboard: `http://localhost:8000/dashboard`
- Redis (optional): `localhost:6379`

---

## Exact TradingView Alert Creation Steps

1. Open a SPY chart in TradingView.
2. Paste `pine/spy_0dte_scalper.pine` into Pine Editor, then **Add to chart**.
3. Click **Create Alert**.
4. Under condition, choose this strategy.
5. Trigger type: **Order fills and alert() function calls**.
6. Set **Webhook URL** to:
   - `http://localhost:8000/webhook/tradingview` (local), or
   - your hosted URL.
7. Ensure the alert message is valid JSON (script emits JSON automatically).
8. Save alert and verify events in `/dashboard-api/alerts` or `/dashboard`.

More detail: `docs/tradingview_webhook_setup.md`.

---

## Example Webhook JSON

```json
{
  "ticker": "SPY",
  "time": "2026-05-19T14:01:12Z",
  "price": "525.40",
  "interval": "1",
  "action": "BUY_CALL",
  "market_position": "flat",
  "setup": "SPY_0DTE_SCALP",
  "bias": "bullish",
  "rsi": "57.80",
  "ema_fast": "525.12",
  "ema_slow": "524.91",
  "macd_state": "bullish_momentum",
  "volume_state": "spike",
  "vwap_state": "above_vwap",
  "atr": "1.15"
}
```

---

## Feature Flags

Controlled in `.env`:
- `AI_FILTERING_ENABLED`
- `NEWS_FILTERING_ENABLED`
- `BROKER_EXECUTION_ENABLED`
- `PAPER_TRADING_MODE` (default `true`)

Risk presets:
- `RISK_PRESET=conservative|standard|aggressive`

---

## Replay / Backtest-style Evaluation of Webhooks

- All webhook payloads + decisions + news snapshots + execution outcomes are stored in DB.
- Replay API: `POST /replay/run?limit=500`
- CLI replay:
  ```bash
  python -m backend.replay --limit 500 --out docs/replay_report.json
  ```
- Replay compares:
  - baseline technical-only outcome
  - Pine + AI filter
  - Pine + AI + risk engine

---

## Known Limitations

1. TradingView webhooks are event-driven and depend on alert delivery reliability/latency.
2. Pine can only use chart-side technical data; external AI/news processing must occur in backend.
3. Paper execution uses synthetic option-chain simulation unless a real broker/data adapter is wired.
4. Real 0DTE fills and spread behavior can differ materially from simulated fills.
5. Event blackout logic is keyword-driven unless enriched by a full economic-calendar feed.

---

## Existing IBKR MVP

The original IBKR LLM assistant remains in:
`ibkr-llm-trading-assistant/`

This new stack is intentionally separate and focused on TradingView -> webhook -> AI/news/risk -> options execution filtering.
