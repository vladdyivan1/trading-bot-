from __future__ import annotations

from datetime import datetime, timezone

from ai.news_providers import NewsHeadline
from ai.sentiment_engine import SentimentEngine


def test_sentiment_detects_event_risk_and_mixed_flow() -> None:
    headlines = [
        NewsHeadline(
            title="S&P 500 rally fades as Powell warns Fed may stay hawkish",
            published_at=datetime.now(timezone.utc),
        ),
        NewsHeadline(
            title="Treasury yields edge lower while tech leads premarket gains",
            published_at=datetime.now(timezone.utc),
        ),
    ]

    analysis = SentimentEngine().analyze(headlines)

    assert analysis.sentiment == "MIXED"
    assert "EVENT_RISK_HEADLINES" in analysis.risk_flags
    assert "MIXED_HEADLINE_FLOW" in analysis.risk_flags


def test_no_news_lowers_confidence_context() -> None:
    analysis = SentimentEngine().analyze([])

    assert analysis.sentiment == "NEUTRAL"
    assert "NO_NEWS_AVAILABLE" in analysis.risk_flags
