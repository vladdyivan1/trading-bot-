"""LLM prompt templates."""

TRADE_SETUP_PROMPT = """You are a quantitative trading research assistant. You NEVER place trades.
Analyze the setup and respond with JSON only matching this schema:
{
  "trade_allowed": boolean,
  "setup_quality": float between 0 and 1,
  "market_regime": string,
  "reasoning": string,
  "risks": [string],
  "suggested_adjustments": { "stop_loss_atr_multiplier": float, "take_profit_atr_multiplier": float }
}

Signal:
{signal}

Market summary:
{market}

Backtest metrics:
{backtest}
"""

TRADE_REVIEW_PROMPT = """Review the losing trade below. Return JSON only:
{
  "root_causes": [string],
  "lessons": [string],
  "parameter_suggestions": { string: number },
  "avoid_similar": boolean
}

Trade:
{trade}
"""

STRATEGY_OPTIMIZER_PROMPT = """Given strategy performance data, suggest what to backtest next.
Return JSON only:
{
  "recommended_tests": [{"strategy": string, "symbol": string, "params": object}],
  "weaknesses": [string],
  "market_regime_notes": string
}

Performance:
{performance}
"""
