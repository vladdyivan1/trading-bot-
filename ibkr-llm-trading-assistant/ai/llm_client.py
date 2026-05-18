"""LLM client — structured JSON responses only, never executes trades."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from loguru import logger

from config.settings import get_settings


class LLMClient:
    """OpenAI or Anthropic wrapper for trading research."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any = None

    def _get_openai_client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.settings.openai_api_key)

    def _get_anthropic_client(self):
        from anthropic import Anthropic

        return Anthropic(api_key=self.settings.anthropic_api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Get completion from configured LLM provider."""
        if self.settings.llm_provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"
        if self.settings.llm_provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            client = self._get_anthropic_client()
            response = client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=2048,
                system=system_prompt + "\nRespond with valid JSON only.",
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
            )
            return response.content[0].text
        raise ValueError(f"Unknown LLM provider: {self.settings.llm_provider}")

    @staticmethod
    def parse_json_response(text: str) -> dict:
        """Extract JSON from LLM response."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            logger.error("Failed to parse LLM JSON: {}", text[:200])
            return {}

    def complete_json(
        self, system_prompt: str, user_prompt: str
    ) -> dict:
        raw = self.complete(system_prompt, user_prompt)
        return self.parse_json_response(raw)

    def is_available(self) -> bool:
        if self.settings.llm_provider == "openai":
            return bool(self.settings.openai_api_key)
        if self.settings.llm_provider == "anthropic":
            return bool(self.settings.anthropic_api_key)
        return False
