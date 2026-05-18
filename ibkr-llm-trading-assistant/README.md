# IBKR LLM Trading Assistant

A modular Python trading system that connects to Interactive Brokers (IB Gateway / TWS), backtests strategies, uses an LLM as a **research assistant only**, scores setups with ML, and executes **paper trades** through a deterministic risk manager.

> **Safety first:** The LLM never places trades. Python handles backtesting, risk checks, and order execution.

## Features

- **IBKR integration** — stocks, ETFs, forex (options/futures architecture ready)
- **Historical data** — multi-timeframe OHLCV with SQLite cache
- **Backtesting** — commissions, slippage, stops, targets, full metrics
- **Strategies** — MA crossover, RSI mean reversion, breakout
- **ML scoring** — LightGBM/sklearn direction classifier with walk-forward validation
- **LLM assistant** — structured JSON reviews (OpenAI or Anthropic)
- **Risk manager** — hard limits, kill switch, paper-only by default
- **Streamlit dashboard** — connection, data, backtests, AI panel, paper trading

## Requirements

- Python 3.11+
- IB Gateway or TWS (paper account recommended)
- OpenAI or Anthropic API key (optional, for LLM features)

## Installation

```bash
cd ibkr-llm-trading-assistant
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys and IBKR settings
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `IBKR_HOST` | Default `127.0.0.1` |
| `IBKR_PORT` | `7497` paper, `7496` live |
| `IBKR_PAPER` | `true` for paper trading |
| `LIVE_TRADING_ENABLED` | **`false` by default** |
| `OPENAI_API_KEY` | For LLM analysis |
| `DATABASE_URL` | SQLite path |

## Connect IB Gateway (Paper)

1. Install [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
2. Log in with your **paper** account
3. Enable API: Configure → Settings → API → Enable ActiveX and Socket Clients
4. Set port **7497** for paper
5. Add `127.0.0.1` to trusted IPs

## Usage

### Initialize database

```bash
python app/main.py init
```

### Download historical data

```bash
python app/main.py download SPY --timeframe "5 mins"
python app/main.py download EURUSD --asset-class CASH --timeframe "1 hour"
```

### Run a backtest

```bash
python app/main.py backtest SPY --strategy ma_crossover --timeframe "5 mins"
```

### Full MVP pipeline (signal → backtest → LLM → risk → paper trade)

```bash
python app/main.py trade SPY --strategy ma_crossover
```

### Streamlit dashboard

```bash
streamlit run app/dashboard.py
```

## Architecture

```
Signal (Strategy) → Backtest Check → ML Score → LLM Review (advisory)
       → Risk Manager (deterministic) → Execution Engine → IBKR Paper
```

| Layer | Role |
|-------|------|
| `strategies/` | Generate structured `TradeSignal` objects |
| `backtesting/` | Deterministic performance evaluation |
| `models/` | ML setup scoring (no profit guarantees) |
| `ai/` | JSON-only research output |
| `risk/` | Blocks unsafe trades, position sizing |
| `execution/` | Places orders only after approval |
| `broker/` | ib_insync IBKR wrapper |

## LLM Layer

The LLM analyzes setups and returns JSON such as:

```json
{
  "trade_allowed": true,
  "setup_quality": 0.78,
  "market_regime": "bullish trend",
  "reasoning": "...",
  "risks": ["High spread"],
  "suggested_adjustments": {"stop_loss_atr_multiplier": 1.5}
}
```

Even when `trade_allowed` is `true`, the **risk manager** must still approve the trade.

## Why Live Trading Is Disabled

Live trading can cause real financial loss. By default:

- `LIVE_TRADING_ENABLED=false`
- `PAPER_TRADING_ENABLED=true`
- `IBKR_PORT=7497` (paper)

To enable live trading later (not recommended without thorough testing):

1. Set `LIVE_TRADING_ENABLED=true` in `.env`
2. Use live IBKR port `7496`
3. Set `IBKR_PAPER=false`
4. Review all risk limits manually

## Self-Improvement Loop

The system logs signals, trades, backtests, and LLM recommendations. `StrategyOptimizer` ranks strategies and suggests parameters, but **requires human approval** before promoting any strategy to live trading.

## Testing

```bash
cd ibkr-llm-trading-assistant
pytest -v
```

## Project Structure

See repository tree: `broker/`, `data/`, `strategies/`, `backtesting/`, `ai/`, `models/`, `risk/`, `execution/`, `database/`, `app/`.

## Roadmap

- **Phase 1** ✓ Structure, IBKR, data, backtest
- **Phase 2** ✓ Risk, paper trading, dashboard
- **Phase 3** ✓ LLM, ML, performance review
- **Phase 4** Options, futures, advanced portfolio risk

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Past backtest performance does not guarantee future results. The ML model does not guarantee profits.
