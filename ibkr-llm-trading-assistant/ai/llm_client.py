"""LLM client for OpenAI, Anthropic, or mock mode."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from config.settings import Settings, get_settings


class LLMClient:
    """Unified LLM interface — returns parsed JSON dicts."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Request structured JSON from the configured LLM provider."""
        if self.settings.llm_provider == "mock":
            return self._mock_response(user)
        if self.settings.llm_provider == "openai":
            return self._openai(system, user)
        if self.settings.llm_provider == "anthropic":
            return self._anthropic(system, user)
        raise ValueError(f"Unknown LLM provider: {self.settings.llm_provider}")

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("{"):
            return json.loads(text)
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError("No JSON found in LLM response")

    def _openai(self, system: str, user: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            logger.warning("No OpenAI API key; using mock")
            return self._mock_response(user)
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        resp = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system + "\nRespond with valid JSON only."},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return self._extract_json(resp.choices[0].message.content or "{}")

    def _anthropic(self, system: str, user: str) -> dict[str, Any]:
        if not self.settings.anthropic_api_key:
            logger.warning("No Anthropic API key; using mock")
            return self._mock_response(user)
        import anthropic

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        resp = client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1024,
            system=system + "\nRespond with valid JSON only.",
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text if resp.content else "{}"
        return self._extract_json(text)

    def _mock_response(self, user: str) -> dict[str, Any]:
        """Deterministic mock for offline development and tests."""
        return {
            "trade_allowed": True,
            "setup_quality": 0.75,
            "market_regime": "neutral",
            "reasoning": "Mock LLM analysis for development. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for real analysis.",
            "risks": ["Mock mode — not real analysis"],
            "suggested_adjustments": {
                "stop_loss_atr_multiplier": 1.5,
                "take_profit_atr_multiplier": 2.0,
            },
        }
