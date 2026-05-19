"""News headline providers with mock for offline dev."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import random

from backend.config import Settings, get_settings


@dataclass
class NewsBundle:
    headlines: list[dict] = field(default_factory=list)
    sentiment: str = "NEUTRAL"
    event_risk: bool = False
    fetched_at: datetime = field(default_factory=datetime.utcnow)


class NewsProvider(ABC):
    @abstractmethod
    async def fetch_headlines(self, symbol: str) -> NewsBundle:
        pass


class MockNewsProvider(NewsProvider):
    """Deterministic-ish mock for tests and offline development."""

    SCENARIOS = {
        "risk_on": [
            {"title": "S&P 500 futures rise as tech leads pre-market", "source": "mock", "score": 0.6},
            {"title": "Treasury yields ease; risk appetite improves", "source": "mock", "score": 0.4},
        ],
        "risk_off": [
            {"title": "SPY under pressure amid geopolitical headlines", "source": "mock", "score": -0.7},
            {"title": "VIX climbs as traders hedge index exposure", "source": "mock", "score": -0.5},
        ],
        "event": [
            {"title": "Fed Chair Powell speech at 2:00 PM ET", "source": "mock", "score": 0.0},
            {"title": "CPI report due tomorrow — markets cautious", "source": "mock", "score": -0.2},
        ],
        "neutral": [
            {"title": "SPY trades near prior close in light volume", "source": "mock", "score": 0.05},
        ],
    }

    def __init__(self, scenario: str | None = None):
        self.scenario = scenario

    async def fetch_headlines(self, symbol: str) -> NewsBundle:
        key = self.scenario or random.choice(list(self.SCENARIOS.keys()))
        headlines = self.SCENARIOS.get(key, self.SCENARIOS["neutral"])
        event_risk = key == "event"
        scores = [h["score"] for h in headlines]
        avg = sum(scores) / len(scores) if scores else 0
        if event_risk:
            sentiment = "MIXED"
        elif avg > 0.25:
            sentiment = "BULLISH"
        elif avg < -0.25:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
        return NewsBundle(headlines=headlines, sentiment=sentiment, event_risk=event_risk)


class FinnhubNewsProvider(NewsProvider):
    """Finnhub market news — requires FINNHUB_API_KEY."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_headlines(self, symbol: str) -> NewsBundle:
        import httpx

        if not self.api_key:
            return await MockNewsProvider().fetch_headlines(symbol)

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": self.api_key},
            )
            r.raise_for_status()
            items = r.json()[:15]

        headlines = [
            {"title": i.get("headline", ""), "source": i.get("source", ""), "score": 0.0}
            for i in items
        ]
        return NewsBundle(headlines=headlines, sentiment="NEUTRAL", event_risk=False)


def get_news_provider(settings: Settings | None = None) -> NewsProvider:
    settings = settings or get_settings()
    if settings.news_provider == "finnhub" and settings.finnhub_api_key:
        return FinnhubNewsProvider(settings.finnhub_api_key)
    return MockNewsProvider()
