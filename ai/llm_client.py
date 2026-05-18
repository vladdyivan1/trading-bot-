"""LLM client that returns validated JSON recommendations only."""

from __future__ import annotations

import json
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from ai.prompts import SYSTEM_PROMPT
from config.settings import settings


class LLMTradeReview(BaseModel):
    trade_allowed: bool
    setup_quality: float = Field(ge=0, le=1)
    market_regime: str
    reasoning: str
    risks: list[str] = Field(default_factory=list)
    suggested_adjustments: dict[str, Any] = Field(default_factory=dict)


class LLMClient:
    """Provider-neutral LLM wrapper with explicit structured output parsing."""

    def __init__(self, provider: Literal["openai", "anthropic"] | None = None) -> None:
        self.provider = provider or ("openai" if settings.openai_api_key else "anthropic")

    def review_trade(self, payload: dict[str, Any], prompt: str) -> LLMTradeReview:
        """Ask the LLM to review a trade setup. Falls back safely if unavailable."""

        try:
            raw = self._complete_json(prompt=prompt, payload=payload)
            parsed = json.loads(raw)
            return LLMTradeReview(**parsed)
        except (ImportError, RuntimeError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM review unavailable or invalid: {}", exc)
            return LLMTradeReview(
                trade_allowed=False,
                setup_quality=0.0,
                market_regime="unknown",
                reasoning="LLM review unavailable or returned invalid JSON; deterministic system blocks AI approval.",
                risks=["LLM unavailable"],
                suggested_adjustments={},
            )

    def _complete_json(self, prompt: str, payload: dict[str, Any]) -> str:
        if self.provider == "openai":
            return self._openai_complete(prompt, payload)
        return self._anthropic_complete(prompt, payload)

    def _openai_complete(self, prompt: str, payload: dict[str, Any]) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{prompt}\n\nPayload:\n{json.dumps(payload, default=str)}"},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty content")
        return content

    def _anthropic_complete(self, prompt: str, payload: dict[str, Any]) -> str:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1000,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{prompt}\n\nPayload:\n{json.dumps(payload, default=str)}"}],
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_parts:
            raise RuntimeError("Anthropic returned empty content")
        return "".join(text_parts)
