# Architecture

This system separates signal generation from trade approval:

1. TradingView Pine Script emits technical SPY scalp setups and JSON alerts.
2. FastAPI validates and normalizes webhook payloads.
3. News and AI modules filter and score trade opportunities in real time.
4. Risk rules reject stale, duplicate, out-of-session, over-limit, or unsafe options trades.
5. The execution adapter defaults to paper trading. Live broker adapters are stubs until explicitly implemented and enabled.
6. Every alert, news snapshot, decision, order, and position is persisted for replay and dashboard analytics.

Pine Script does not call an LLM, broker, or news API. The TradingView webhook URL is configured in the TradingView alert dialog.
