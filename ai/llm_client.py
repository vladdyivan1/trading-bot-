"""LLM client abstraction with strict JSON output parsing."""

        from __future__ import annotations

        import json
        from typing import Any

        from pydantic import BaseModel, Field

        from ai.prompts import TRADE_REVIEW_SYSTEM_PROMPT
        from config.settings import Settings, get_settings


        class LLMTradeReview(BaseModel):
            trade_allowed: bool = False
            setup_quality: float = Field(default=0.0, ge=0, le=1)
            market_regime: str = "unknown"
            reasoning: str = "LLM unavailable; used deterministic fallback."
            risks: list[str] = Field(default_factory=list)
            suggested_adjustments: dict[str, float] = Field(default_factory=dict)


        class LLMClient:
            """Provider-agnostic LLM interface that enforces JSON-only responses."""

            def __init__(self, settings: Settings | None = None) -> None:
                self.settings = settings or get_settings()

            def analyze(self, payload: dict[str, Any], user_prompt: str) -> LLMTradeReview:
                provider = self.settings.llm_provider

                if provider == "openai" and self.settings.openai_api_key:
                    result = self._call_openai(payload, user_prompt)
                    if result is not None:
                        return result

                if provider == "anthropic" and self.settings.anthropic_api_key:
                    result = self._call_anthropic(payload, user_prompt)
                    if result is not None:
                        return result

                return self._fallback(payload)

            def _call_openai(self, payload: dict[str, Any], user_prompt: str) -> LLMTradeReview | None:
                try:
                    from openai import OpenAI

                    client = OpenAI(api_key=self.settings.openai_api_key)
                    prompt = f"{user_prompt}

Context JSON:
{json.dumps(payload, default=str)}"
                    response = client.chat.completions.create(
                        model=self.settings.openai_model,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": TRADE_REVIEW_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                    )
                    content = response.choices[0].message.content or "{}"
                    return LLMTradeReview.model_validate_json(content)
                except Exception:
                    return None

            def _call_anthropic(self, payload: dict[str, Any], user_prompt: str) -> LLMTradeReview | None:
                try:
                    import anthropic

                    client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
                    prompt = (
                        f"{TRADE_REVIEW_SYSTEM_PROMPT}

{user_prompt}

"
                        f"Return JSON only. Context:
{json.dumps(payload, default=str)}"
                    )
                    msg = client.messages.create(
                        model=self.settings.anthropic_model,
                        max_tokens=800,
                        temperature=0.1,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = ""
                    for block in msg.content:
                        if hasattr(block, "text"):
                            raw += block.text
                    raw = raw.strip()
                    return LLMTradeReview.model_validate_json(raw)
                except Exception:
                    return None

            def _fallback(self, payload: dict[str, Any]) -> LLMTradeReview:
                confidence = float(payload.get("signal", {}).get("confidence_score", 0.0))
                expectancy = float(payload.get("backtest", {}).get("expectancy", 0.0))
                trade_allowed = confidence >= 0.65 and expectancy > 0
                market_regime = payload.get("market_summary", {}).get("trend", "unknown")
                risks = []
                if confidence < 0.65:
                    risks.append("Low confidence signal")
                if expectancy <= 0:
                    risks.append("Backtest expectancy non-positive")
                if not risks:
                    risks.append("No major deterministic risks found")
                return LLMTradeReview(
                    trade_allowed=trade_allowed,
                    setup_quality=min(1.0, max(0.0, (confidence + (0.55 if expectancy > 0 else 0.25)) / 1.55)),
                    market_regime=market_regime,
                    reasoning="Fallback heuristic used because configured LLM was unavailable.",
                    risks=risks,
                    suggested_adjustments={
                        "stop_loss_atr_multiplier": 1.5,
                        "take_profit_atr_multiplier": 2.0,
                    },
                )
