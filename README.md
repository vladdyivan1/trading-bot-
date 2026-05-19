# SPY 0DTE Options Scalping System

Production-oriented **AI-assisted 0DTE/1DTE SPY options scalping** stack:

- **TradingView (Pine Script v5)** — technical signals + JSON webhook alerts only (no LLM in Pine)
- **FastAPI backend** — validates alerts, enriches news/sentiment, applies risk, paper execution
- **AI/news layer** — filters and scores trade opportunities in real time (probabilistic, not predictive)
- **Dashboard** — alerts, decisions, PnL, sentiment heatmap, regime analytics

Default mode is **paper trading**. Live broker execution requires explicit config.

## Architecture

```text
TradingView Alert (JSON)
        │
        ▼
POST /webhook/tradingview
        │
        ├─► Normalize + persist alert
        ├─► News provider (mock | NewsAPI)
        ├─► AI decision engine (mock | OpenAI)
        ├─► Risk engine (presets: conservative / standard / aggressive)
        ├─► Options selector (0DTE/1DTE, delta, spread, OI)
        └─► Paper executor (or broker adapter stub)
```

## Project layout

```text
/pine/spy_0dte_scalper.pine
/backend/          FastAPI app, routes, services, models
/ai/               sentiment, news, LLM decision
/execution/        paper + broker stubs
/dashboard/static/ web UI
/tests/
/docs/             alert templates, TradingView setup
/scripts/replay.py replay historical webhooks
```

## Local run

```bash
cd /workspace
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Dashboard: http://localhost:8000/dashboard/
- Health: http://localhost:8000/health

### Test webhook

```bash
curl -X POST http://localhost:8000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "SPY",
    "time": "2026-05-19T10:15:00-04:00",
    "price": "585.42",
    "bias": "bullish",
    "rsi": "58",
    "ema_fast": "585",
    "ema_slow": "584",
    "macd_state": "bullish",
    "volume_state": "spike",
    "vwap_state": "above",
    "atr": "1.2",
    "secret": "change-me-in-production"
  }'
```

Match `secret` to `WEBHOOK_SECRET` in `.env`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## TradingView setup

See [docs/tradingview_setup.md](docs/tradingview_setup.md) and example payloads in [docs/alert_templates.json](docs/alert_templates.json).

**Summary:**

1. Add `pine/spy_0dte_scalper.pine` to chart (SPY, 1m/3m).
2. Create alert: strategy → **Any alert() function call**.
3. Set **Webhook URL** to `https://YOUR_HOST/webhook/tradingview` (HTTPS required for production).
4. Use JSON message with `{{ticker}}`, `{{timenow}}`, `{{close}}`, etc.

## Feature flags (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_AI_FILTER` | true | AI approve/reject/wait |
| `ENABLE_NEWS_FILTER` | true | Headline fetch + event risk |
| `ENABLE_BROKER_EXECUTION` | false | Live brokers (stubs only in MVP) |
| `EXECUTION_MODE` | paper | `paper` or `live` |
| `AI_PROVIDER` | mock | `mock` or `openai` |
| `NEWS_PROVIDER` | mock | `mock` or `newsapi` |
| `KILL_SWITCH` | false | Halt all trading |

## Replay / backtest filter comparison

```bash
python scripts/replay.py docs/sample_replay.jsonl
```

Save production webhooks to JSONL and re-run through:

- Pine-only ( `--no-ai` )
- Pine + AI (default)
- Adjust risk via `RISK_PRESET`

## Tests

```bash
pytest -q
```

## Known limitations

1. **Pine Script** cannot call external APIs or LLMs; only indicators + alerts.
2. **TradingView webhooks** are best-effort, not co-located HFT; expect second-scale latency.
3. **Options chains** in paper mode use synthetic liquidity; live requires Tradier/IBKR/etc.
4. **0DTE theta/gamma** modeled via time-of-day rejects, not full greeks simulation.
5. **News/sentiment** is filtering/scoring, not price prediction.
6. **Alert JSON** must be valid; malformed bodies are rejected.
7. **Simultaneous alerts** deduped via `duplicate_alert_window_seconds`.

## Related

Legacy IBKR assistant remains in [ibkr-llm-trading-assistant/](ibkr-llm-trading-assistant/) — separate from this SPY webhook scalper.
