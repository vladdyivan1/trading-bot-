from __future__ import annotations

from datetime import UTC, datetime

from ai.news_providers import Headline
from ai.sentiment_engine import SentimentEngine
from backend.schemas.decision import NewsSentiment


def test_sentiment_engine_detects_mixed_and_event_risk() -> None:
    engine = SentimentEngine()
    headlines = [
        Headline(
            title="SPY rally extends as inflation cools",
            source="test",
            published_at=datetime.now(UTC),
        ),
        Headline(
            title="Fed decision ahead as geopolitical tensions rise",
            source="test",
            published_at=datetime.now(UTC),
        ),
    ]
    result = engine.evaluate(headlines)
    assert result.sentiment in {NewsSentiment.MIXED, NewsSentiment.NEUTRAL}
    assert any(flag.startswith("EVENT:") for flag in result.risk_flags)
