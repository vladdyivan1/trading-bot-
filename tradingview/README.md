# SPY TradingView P&L Indicator

Pine Script strategy for **SPY** with a built-in profitability panel (net P&L, win rate, profit factor, drawdown) and the same SMA crossover logic used in this repo’s backtests.

## Quick start

1. Open [TradingView](https://www.tradingview.com/chart/) and load **SPY**.
2. Set timeframe to **1D** (daily) for defaults tuned to this strategy.
3. Open **Pine Editor** → **New** → paste the contents of `spy_pl_indicator.pine`.
4. Click **Save** → **Add to chart**.

TradingView treats this as a **strategy** (not a plain indicator) so the Strategy Tester can compute P&L. The on-chart table shows live stats; the bottom **Strategy Tester** tab shows full trade history.

## What it does

| Feature | Default |
|--------|---------|
| Signal | 10 / 30 SMA crossover (matches `moving_average_crossover` in the Python bot) |
| RSI filter | On — long when RSI ≥ 45, optional shorts when RSI ≤ 55 |
| Stops / targets | ATR-based (1.5× stop, 2.0× target) |
| Shorts | Off by default (typical SPY long-only) |
| P&L panel | Net P&L, open P&L, win rate, profit factor, trades, drawdown, equity |

## Recommended settings for SPY

- **Symbol:** SPY  
- **Timeframe:** Daily  
- **Initial capital:** $100,000 (editable in strategy properties)  
- **Allow short trades:** Off unless you explicitly want mean-reversion shorts  

## Inputs you may want to tune

- **Fast / Slow SMA** — crossover periods  
- **RSI filter** — reduces whipsaws in choppy markets  
- **Stop / Target ATR multiples** — risk/reward per trade  
- **Panel position** — move the P&L table to any corner  

## Notes

- Past performance in the Strategy Tester is **not** a guarantee of future results.
- Add realistic **commission** and **slippage** in strategy settings before trusting profitability.
- For intraday SPY, lower the SMA periods and RSI thresholds in the inputs.
