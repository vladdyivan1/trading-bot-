# ibkr-llm-trading-assistant

Production-quality MVP for an LLM-assisted automated trading research and paper-trading system for Interactive Brokers.

The system is intentionally safety-first: the LLM never places orders. It can analyze market context, review backtests, suggest parameter changes, and return structured recommendations. Deterministic Python code handles signal generation, backtesting, risk controls, order validation, and IBKR execution.

## Features

- Connect to IB Gateway or TWS with `ib_insync`
- Paper trading by default; live trading disabled in configuration
- Qualify stocks/ETFs, forex, futures, and options contracts
- Download and cache historical candles in SQLite
- Backtest moving-average, RSI, and breakout strategies
- Track trades, commissions, slippage, stops, targets, and equity curves
- Calculate return, CAGR, win rate, profit factor, drawdown, expectancy, Sharpe, Sortino, trade count, and average hold time
- Train baseline predictive models using scikit-learn with walk-forward validation
- Use OpenAI or Anthropic for structured JSON-only trade research assistance
- Enforce hard-coded risk checks before paper order placement
- Log signals, trades, LLM recommendations, and performance feedback
- Streamlit dashboard for connection status, downloads, backtests, AI review, risk settings, and kill switch

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Python 3.11+ is recommended.

## Environment setup

Copy the example environment file and adjust values:

```bash
cp .env.example .env
```

Important defaults:

- `TRADING_MODE=paper`
- `ENABLE_LIVE_TRADING=false`
- `IBKR_HOST=127.0.0.1`
- `IBKR_PORT=7497` for TWS paper trading, or `4002` for IB Gateway paper trading
- `IBKR_CLIENT_ID=101`

Add one LLM API key if you want AI reviews:

```dotenv
OPENAI_API_KEY=...
# or
ANTHROPIC_API_KEY=...
```

## IB Gateway / TWS paper trading

1. Start TWS or IB Gateway.
2. Log into a paper account.
3. Enable API access.
4. Confirm socket port matches `.env`:
   - TWS paper: `7497`
   - Gateway paper: `4002`
5. Keep live trading disabled unless you intentionally update the config.

## Download historical data

From Python:

```python
from broker.ibkr_client import IBKRClient
from data.historical_data import HistoricalDataService
from data.data_store import HistoricalDataStore

client = IBKRClient()
client.connect()
store = HistoricalDataStore()
svc = HistoricalDataService(client, store)
df = svc.get_or_fetch("SPY", "STK", "1 day", duration="5 Y")
```

Supported timeframes include `1 min`, `5 mins`, `15 mins`, `1 hour`, and `1 day`.

## Run a backtest

```python
from data.data_store import HistoricalDataStore
from strategies.moving_average_strategy import MovingAverageCrossoverStrategy
from backtesting.engine import BacktestEngine

store = HistoricalDataStore()
bars = store.load_bars("SPY", "STK", "SMART", "USD", "1 day")
strategy = MovingAverageCrossoverStrategy(symbol="SPY", asset_class="STK", timeframe="1 day")
result = BacktestEngine().run(bars, strategy)
print(result.metrics)
```

## Dashboard

```bash
streamlit run app/dashboard.py
```

The dashboard includes:

- IBKR connection settings/status
- Account summary placeholder
- Historical data downloader
- Backtest runner and strategy comparison
- Equity curve chart
- Trade log
- AI analysis panel
- Risk settings
- Kill switch controls

## LLM layer

The LLM layer accepts structured market summaries, backtest metrics, and trade logs. It returns JSON matching the `LLMTradeReview` schema:

```json
{
  "trade_allowed": true,
  "setup_quality": 0.78,
  "market_regime": "bullish trend",
  "reasoning": "Price is above VWAP and 20 EMA, volatility is expanding, and backtest expectancy is positive.",
  "risks": ["High spread"],
  "suggested_adjustments": {
    "stop_loss_atr_multiplier": 1.5,
    "take_profit_atr_multiplier": 2.0
  }
}
```

LLM output is advisory only. It must pass deterministic validation and risk checks before paper execution.

## Safety and live trading

Live trading is disabled by default because automated order placement can cause real financial losses. To safely enable live trading later:

1. Complete extended paper-trading validation.
2. Review broker permissions and order types.
3. Add environment-specific controls for account IDs and allowed symbols.
4. Add human approval for strategy promotion.
5. Set `ENABLE_LIVE_TRADING=true` only after code review and operational approval.

The default risk policy includes:

- Max risk per trade: 0.5% of account equity
- Max daily loss: 2% of account equity
- Max open positions: 3
- Minimum reward-to-risk: 1.5
- Minimum model confidence: 0.65
- Paper trading only
- Manual kill switch

## Tests

```bash
pytest
```

Tests cover backtest metrics, strategy signal generation, position sizing, risk blocking logic, and candle validation.

## Project phases

- Phase 1: Project structure, IBKR connection, historical data, SQLite storage, simple strategies, backtesting
- Phase 2: Risk manager, paper trading, dashboard, trade logging
- Phase 3: LLM assistant, predictive model, strategy performance review
- Phase 4: Options/futures expansion, advanced portfolio risk, optimization
