"""LLM prompt templates."""

SYSTEM_PROMPT = """You are a quantitative trading research assistant.
You analyze market data, backtest results, and trade logs.
You NEVER place trades or give direct execution commands.
You ONLY respond with valid JSON matching the requested schema.
Be conservative: highlight risks, drawdowns, and overfitting concerns.
Do not guarantee profits. Focus on risk-adjusted returns and expectancy."""

TRADE_REVIEW_PROMPT = """Review this trade setup and respond with JSON only:
{
  "trade_allowed": boolean,
  "setup_quality": float (0-1),
  "market_regime": string,
  "reasoning": string,
  "risks": [strings],
  "suggested_adjustments": {"stop_loss_atr_multiplier": float, "take_profit_atr_multiplier": float},
  "suggested_backtests": [strings],
  "strategy_weaknesses": [strings]
}

Signal: {signal}
Market summary: {market_summary}
Backtest metrics: {backtest_metrics}
Recent performance: {performance}"""

STRATEGY_OPTIMIZER_PROMPT = """Analyze strategy performance and suggest improvements.
Respond with JSON only:
{
  "parameter_suggestions": {{"param": value}},
  "weaknesses": [strings],
  "recommended_backtests": [strings],
  "promotion_ready": false,
  "requires_human_approval": true,
  "reasoning": string
}

Strategy: {strategy_name}
Performance by symbol: {performance}
Walk-forward results: {walk_forward}"""

LOSING_TRADE_REVIEW_PROMPT = """Review this losing trade and explain what went wrong.
Respond with JSON:
{
  "root_causes": [strings],
  "market_regime_at_entry": string,
  "lessons": [strings],
  "parameter_adjustments": {{}}
}

Trade: {trade}
Context: {context}"""

MARKET_REGIME_PROMPT = """Summarize the current market regime from this data.
Respond with JSON:
{
  "regime": string,
  "volatility": string,
  "trend_strength": float,
  "key_levels": [floats],
  "risks": [strings]
}

Data: {market_data}"""
