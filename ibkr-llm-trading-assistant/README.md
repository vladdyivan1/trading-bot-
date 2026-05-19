# IBKR LLM Trading Assistant

A modular Python trading system that connects to **Interactive Brokers** (IB Gateway / TWS), downloads historical data, backtests strategies, uses an **LLM as a research assistant** (not an execution bot), trains predictive models, and places **paper trades** only after deterministic risk checks pass.

> **Safety first:** The LLM never places orders. Python code handles backtesting, risk management, order validation, and execution.

## Features

- IBKR connection (paper by default) via `ib_insync`
- Historical OHLCV download and SQLite storage (up to 5 years daily)
- Deterministic backtesting with full metrics
- Strategy framework: MA crossover, RSI mean reversion, breakout
- ML direction model with walk-forward validation
- LLM setup analysis (OpenAI / Anthropic / mock)
- Risk manager with kill switch
- Paper trade execution pipeline
- Streamlit dashboard
- Performance feedback and strategy ranking

## Asset classes

| Phase | Asset class | Status |
|-------|-------------|--------|
| 1–3 | Stocks, ETFs, Forex | Supported |
| 4 | Options, Futures | Architecture ready (`broker/contracts.py`) |

## Requirements

- Python 3.11+
- IB Gateway or TWS (paper account recommended)
- Optional: OpenAI or Anthropic API key for LLM analysis

## Installation

```bash
cd ibkr-llm-trading-assistant
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
```

## Environment setup

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `IBKR_HOST` | Default `127.0.0.1` |
| `IBKR_PORT` | Paper Gateway often `4002`, TWS paper `7497` |
| `IBKR_CLIENT_ID` | Unique client id |
| `PAPER_TRADING` | `true` (default) |
| `LIVE_TRADING_ENABLED` | `false` (default) |
| `LLM_PROVIDER` | `mock`, `openai`, or `anthropic` |
| `OPENAI_API_KEY` | Required if using OpenAI |

## Connect IB Gateway (paper)

1. Install [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) or TWS.
2. Log in with your **paper** account.
3. Enable API: Configure → Settings → API → Enable ActiveX and Socket Clients.
4. Set socket port (e.g. `4002` for Gateway paper).
5. Set `IBKR_PORT` in `.env` to match.

## Quick start

### Download historical data

```bash
python app/main.py download SPY --timeframe "1 day" --years 5
```

Requires IBKR connection for live download. Data is cached in SQLite (`data/trading.db`).

### Run a backtest

```bash
python app/main.py backtest SPY --strategy moving_average_crossover --export trades.csv
```

### LLM analysis (mock mode without API key)

```bash
python app/main.py analyze SPY --strategy rsi_mean_reversion
```

Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` for real analysis.

### Full paper trade pipeline

```bash
python app/main.py trade SPY --strategy moving_average_crossover
```

Flow: **signal → LLM review → risk manager → paper order** (if all pass).

### Train ML model

```bash
python app/main.py train-model SPY
```

### Dashboard

```bash
streamlit run app/dashboard.py
```

Tabs: Connection, Data, Backtest, AI Analysis, Paper Trading, Risk (kill switch).

## Project structure

```
ibkr-llm-trading-assistant/
  config/settings.py      # Environment & risk defaults
  broker/                 # IBKR client, contracts, orders
  data/                   # Historical download & SQLite store
  strategies/             # Signal generation
  backtesting/            # Engine, metrics, walk-forward
  ai/                     # LLM client (no order placement)
  models/                 # Feature engineering & ML
  risk/                   # Risk manager, position sizing, kill switch
  execution/              # Paper/live traders, execution engine
  database/               # SQLAlchemy models & repositories
  app/                    # CLI & Streamlit dashboard
  tests/
```

## How the LLM layer works

1. Strategies produce a structured `TradeSignal` (Pydantic).
2. `SignalAnalyzer` sends signal + market summary + backtest stats to the LLM.
3. LLM returns JSON: `trade_allowed`, `setup_quality`, `risks`, etc.
4. `RiskManager` applies hard rules (drawdown, R:R, confidence, kill switch).
5. `ExecutionEngine` places a **paper** order only if both approve.

The LLM cannot call `place_order` — only `PaperTrader` does, after risk approval.

## Why live trading is disabled by default

- `LIVE_TRADING_ENABLED=false` in `.env`
- `LiveTrader` requires `human_approved=True`
- `StrategyOptimizer` never sets `approved_for_live=True` automatically

## Safely enabling live trading (later)

1. Thoroughly validate strategies in paper mode.
2. Set `PAPER_TRADING=false` only when using a live account (not recommended until ready).
3. Set `LIVE_TRADING_ENABLED=true` in `.env`.
4. Pass `human_approved=True` to `LiveTrader.execute()`.
5. Keep kill switch accessible in the dashboard.

**Not recommended until you have audited performance, risk limits, and operational procedures.**

## Risk defaults

| Setting | Default |
|---------|---------|
| Max risk per trade | 0.5% of account |
| Max daily loss | 2% |
| Max open positions | 3 |
| Min reward:risk | 1.5 |
| Min model confidence | 0.65 |

## Testing

```bash
cd ibkr-llm-trading-assistant
pytest -v
```

## Development phases

- **Phase 1:** IBKR, data, strategies, backtest ✅
- **Phase 2:** Risk, paper trading, dashboard, logging ✅
- **Phase 3:** LLM, ML model, performance review ✅
- **Phase 4:** Options, futures, advanced portfolio risk (stubs in place)

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Past backtest performance does not guarantee future results. The ML model does not guarantee profits. You are responsible for compliance with broker terms and applicable regulations.
