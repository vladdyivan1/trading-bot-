# SPY TradingView Scripts

Pine Script tools for **SPY** — daily swing P&L backtests and **intraday options scalp** confluence alerts.

## Scripts

| File | Use case |
|------|----------|
| `spy_pl_indicator.pine` | Daily SMA crossover with built-in P&L panel |
| `spy_options_scalp.pine` | Intraday scalp stack: VWAP + 9/20 EMA, RSI, VIX/TICK, volume — **3 setups + confluence alerts** |

---

## SPY Options Scalp Stack (`spy_options_scalp.pine`)

Implements the core indicator stack and three concrete scalp setups from standard SPY options day-trading playbooks:

### Core stack (always on chart)

- **Trend / mean:** VWAP + 9 EMA + 20 EMA (optional 50/200 MA)
- **HTF bias:** 15m + 60m price vs 20 EMA (both must agree)
- **Momentum:** 1m RSI (configurable) crossing 50 + MACD histogram turn
- **Volatility / sentiment:** VIX minimum filter + NYSE TICK panel
- **Volume:** vs 10-bar MA + prior-bar expansion

### Setup 1 — VWAP trend pullback (best on **5m** chart)

**Goal:** Continuation after a controlled pullback in the intraday trend.

**Long confluence (all required):**
1. 15m + 60m bullish bias
2. Close > VWAP, close > 20 EMA, 9 EMA > 20 EMA
3. Pullback touches 9/20 EMA band without closing below VWAP
4. 1m RSI dipped 40–50, then reclaimed 50 (or MACD hist turns up)
5. Volume spike vs MA and prior 3 bars

**Short:** Mirror conditions.

**Alert:** `S1 Trend pullback LONG` / `SHORT`

### Setup 2 — VIX + TICK impulse (best on **1m** chart)

**Goal:** Quick impulse scalps when the market is actively moving.

**Long confluence:**
1. VIX ≥ threshold (default 16)
2. Above VWAP + 20 EMA, 9 > 20 EMA
3. TICK held above floor, crossed up through mid-line
4. 1m RSI crossed above 50
5. Volume > MA and > prior N bars

**Alert:** `S2 VIX+TICK impulse LONG` / `SHORT`

### Setup 3 — Volume profile ledge reversal (best on **5m** chart)

**Goal:** Fade exhaustion at a manually marked VP ledge.

**Setup:**
1. Enter **Ledge high** / **Ledge low** inputs from your volume profile
2. Price tags the ledge zone
3. RSI overbought (>70) or oversold (<30) + rejection wick
4. Close back inside prior range + volume ≥ 1.5× MA

**Alert:** `S3 VP ledge LONG` / `SHORT`

---

## Recommended chart layout

| Panel | Timeframe | Script |
|-------|-----------|--------|
| Bias | 15m or 1h | Watch structure + 20 EMA (no script required) |
| Execution A | **5m** | `spy_options_scalp.pine` — Setup 1 & 3 |
| Execution B | **1m** | `spy_options_scalp.pine` — Setup 2 |

Use **both 1m and 5m** if you trade both entry styles: 5m for pullback context, 1m for impulse entries.

---

## Quick start

1. Open TradingView → chart **SPY**.
2. Add a **5m** chart (and optionally a **1m** layout in another tab).
3. Pine Editor → paste `spy_options_scalp.pine` → **Add to chart**.
4. Confirm **VIX** (`CBOE:VIX`) and **TICK** (`USI:TICK`) symbols resolve on your plan.
5. For Setup 3, set **Ledge high/low** from your volume profile each session.
6. **Alerts** → choose a confluence alert (not single-indicator):
   - `S1 Trend pullback LONG`
   - `S2 VIX+TICK impulse LONG`
   - `S3 VP ledge SHORT`
   - `ANY setup LONG (confluence)` — any of the three

---

## Alert design (confluence only)

Each alert fires only when **trend + momentum + volume** (and VIX/TICK for S2) align. Expect roughly **5–20 quality alerts per session**, not hundreds.

| Alert | Minimum conditions |
|-------|-------------------|
| S1 Long | HTF bull + VWAP/EMA trend + pullback + RSI reclaim + volume |
| S2 Long | VIX ok + trend + TICK turn + RSI cross 50 + volume |
| S3 Short | Ledge zone + RSI OB + rejection + volume |

---

## Options execution notes (manual — not auto-traded)

- **Strike:** 0.20–0.40 delta, same-day or next-day SPY weeklies
- **Stop:** Beyond pullback swing / 20–30% premium (define before entry)
- **Target:** 1R–2R or prior intraday high/low / VWAP / HVN
- **Guardrails:** Trade at levels (VWAP, prior day H/L, VP nodes). Log every alert → trade for stats.

---

## Daily P&L backtest (`spy_pl_indicator.pine`)

For **daily** swing stats (not intraday scalps):

1. Chart SPY on **1D**
2. Paste `spy_pl_indicator.pine` → Add to chart
3. Use Strategy Tester + on-chart P&L table

---

## Limitations

- Pine cannot backtest SPY **options** directly — scripts signal on **SPY underlying**; you execute options manually.
- Volume profile ledges are **manual inputs** (TradingView VP is not fully automatable in Pine).
- TICK/VIX require symbols available on your TradingView subscription.
- Past backtest / alert performance is not a guarantee of future results.
