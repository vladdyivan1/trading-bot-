# TradingView — SPY P&L Indicator

Pine Script overlay for **SPY** (works on any symbol) with simulated trades, built-in **P&L**, and **profitability** stats on the chart.

## Install in TradingView

1. Open [TradingView](https://www.tradingview.com/chart/) and load **SPY** (e.g. `AMEX:SPY`).
2. Open **Pine Editor** (bottom panel) → **New** → blank script.
3. Copy the full contents of [`SPY_PL_Indicator.pine`](./SPY_PL_Indicator.pine) into the editor.
4. Click **Save** → **Add to chart**.

## What it does

- **Signals:** 10/30 SMA crossover (same idea as the repo’s moving-average strategy), optional RSI filter.
- **Risk:** Optional stop loss and take profit (% from entry).
- **P&L:** Tracks realized and unrealized P&L in dollars (shares × price move minus commission).
- **Profitability table:** Total P&L, win rate, profit factor, avg win/loss, max drawdown, and a **PROFITABLE / NOT PROFITABLE** label.

## Suggested SPY settings

| Setting | Default | Notes |
|--------|---------|--------|
| Timeframe | 1D or 15m | Daily for swing; intraday for shorter holds |
| Long only | On | Typical buy-and-hold / long SPY bias |
| Shares | 100 | Match your size; P&L scales linearly |
| Only trade RTH | Off | Turn on to limit signals to 09:30–16:00 ET |

## Alerts

Built-in alert conditions: long entry, long exit, and “became profitable” (total P&L crosses above zero).

## Disclaimer

This is a **chart simulation** for education and research—not live brokerage execution. Past simulated P&L does not guarantee future results.
