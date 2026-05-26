# TradingView SPY Strategy

This folder contains Pine Script tools for TradingView.

## SPY Adaptive Trend Pullback with P&L

File: [`spy_adaptive_pl_strategy.pine`](spy_adaptive_pl_strategy.pine)

TradingView only exposes built-in Strategy Tester profit/loss, win rate, drawdown,
and trade metrics from scripts declared with `strategy()`. For that reason this
script is a TradingView strategy rather than a plain `indicator()`, while still
plotting indicator-style overlays, signal markers, ATR stops/targets, and a
custom on-chart P&L dashboard.

### Default behavior

- Optimized conceptually for SPY research.
- Long-only by default to reflect SPY's historical upward bias.
- Optional short trades are available in settings.
- Uses EMA trend alignment, RSI recovery/rejection, MACD confirmation, relative
  volume, ATR-based stop/target levels, and optional ATR trailing stops.
- Includes daily loss and equity drawdown guards that pause new entries.
- Displays net P&L, open P&L, closed trades, win rate, profit factor, daily P&L,
  current drawdown, and risk state on the chart.

### How to use

1. Open SPY in TradingView.
2. Open Pine Editor.
3. Paste the contents of `spy_adaptive_pl_strategy.pine`.
4. Click **Add to chart**.
5. Review results in the **Strategy Tester** tab and the on-chart P&L dashboard.
6. Test multiple timeframes and market regimes before considering paper trading.

### Important limitation

No indicator or strategy can be guaranteed profitable. Treat this script as a
research starting point, not financial advice or a live-trading recommendation.
Backtest assumptions, slippage, commissions, and market regime changes can all
materially affect results.
