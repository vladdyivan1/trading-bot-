"""Prompt templates for structured LLM trading analysis."""

TRADE_REVIEW_SYSTEM_PROMPT = """
You are a trading research assistant. You MUST return JSON only.
Never suggest direct uncontrolled execution. Focus on risk-adjusted analysis.
""".strip()

SIGNAL_ANALYSIS_PROMPT = """
Analyze the trade setup context and return strictly valid JSON:
{
  "trade_allowed": true,
  "setup_quality": 0.0,
  "market_regime": "string",
  "reasoning": "string",
  "risks": ["string"],
  "suggested_adjustments": {
    "stop_loss_atr_multiplier": 1.0,
    "take_profit_atr_multiplier": 1.5
  }
}
""".strip()

STRATEGY_OPTIMIZER_PROMPT = """
Given strategy performance by symbol/timeframe/regime, suggest conservative
parameter experiments to backtest next. Return JSON only.
""".strip()
