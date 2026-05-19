"""News headline providers with mock for offline dev."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

from backend.config import Settings


@dataclass
class Headline:
    title: str
    source: str
    published_at: datetime
    sentiment_score: float = 0.0  # -1 bearish, +1 bullish
    tags: list[str] = field(default_factory=list)


@dataclass
class NewsSnapshotResult:
    headlines: list[dict]
    overall_sentiment: str
    event_risk: bool
    risk_on_score: float = 0.0


class NewsProvider(ABC):
    @abstractmethod
    def fetch_headlines(self, symbol: str) -> NewsSnapshotResult:
        pass


EVENT_KEYWORDS = [
    "fomc", "fed", "powell", "cpi", "inflation", "jobs report",
    "unemployment", "nonfarm", "treasury yield", "rate hike", "rate cut",
    "geopolitical", "war", "earnings",
]


class MockNewsProvider(NewsProvider):
  def fetch_headlines(self, symbol: str) -> NewsSnapshotResult:
      headlines = [
          Headline(
              title="S&P 500 futures steady ahead of session",
              source="mock",
              published_at=datetime.utcnow(),
              sentiment_score=0.1,
              tags=["SPY", "index"],
          ),
          Headline(
              title="Treasury yields edge higher",
              source="mock",
              published_at=datetime.utcnow(),
              sentiment_score=-0.05,
              tags=["macro", "yields"],
          ),
      ]
      return self._to_snapshot(headlines)

  def _to_snapshot(self, headlines: list[Headline]) -> NewsSnapshotResult:
      scores = [h.sentiment_score for h in headlines]
      avg = sum(scores) / len(scores) if scores else 0
      event_risk = any(
          any(kw in h.title.lower() for kw in EVENT_KEYWORDS) for h in headlines
      )
      if event_risk:
          sentiment = "MIXED"
      elif avg > 0.15:
          sentiment = "BULLISH"
      elif avg < -0.15:
          sentiment = "BEARISH"
      else:
          sentiment = "NEUTRAL"
      return NewsSnapshotResult(
          headlines=[
              {
                  "title": h.title,
                  "source": h.source,
                  "sentiment_score": h.sentiment_score,
                  "tags": h.tags,
              }
              for h in headlines
          ],
          overall_sentiment=sentiment,
          event_risk=event_risk,
          risk_on_score=avg,
      )


class NewsAPIProvider(NewsProvider):
    QUERIES = ["SPY", "S&P 500", "Federal Reserve", "CPI", "unemployment"]

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_headlines(self, symbol: str) -> NewsSnapshotResult:
        headlines: list[Headline] = []
        try:
            with httpx.Client(timeout=5.0) as client:
                for q in self.QUERIES[:3]:
                    resp = client.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            "q": q,
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": 5,
                            "apiKey": self.api_key,
                        },
                    )
                    if resp.status_code != 200:
                        continue
                    for art in resp.json().get("articles", []):
                        headlines.append(
                            Headline(
                                title=art.get("title", ""),
                                source=art.get("source", {}).get("name", "newsapi"),
                                published_at=datetime.utcnow(),
                                sentiment_score=0.0,
                                tags=[q],
                            )
                        )
        except Exception:
            pass
        if not headlines:
            return MockNewsProvider().fetch_headlines(symbol)
        return MockNewsProvider()._to_snapshot(headlines)


def get_news_provider(settings: Settings) -> NewsProvider:
    if settings.news_provider == "newsapi" and settings.newsapi_key:
        return NewsAPIProvider(settings.newsapi_key)
    return MockNewsProvider()
