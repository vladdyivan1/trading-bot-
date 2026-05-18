"""LLM mock client tests."""

from ai.llm_client import LLMClient
from config.settings import Settings


def test_mock_llm_returns_json() -> None:
    client = LLMClient(Settings(llm_provider="mock"))
    result = client.complete_json("system", "user prompt")
    assert "trade_allowed" in result
    assert "setup_quality" in result
