from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import requests


@dataclass(slots=True)
class Headline:
    title: str
    source: str
    published_at: datetime
    url: str | None = None
    symbols: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["published_at"] = self.published_at.isoformat()
        return payload


class NewsProvider(ABC):
    @abstractmethod
    def latest_headlines(self, topics: list[str], limit: int = 12) -> list[Headline]:
        raise NotImplementedError


class MockNewsProvider(NewsProvider):
    def latest_headlines(self, topics: list[str], limit: int = 12) -> list[Headline]:
        now = datetime.now(UTC)
        canned = [
            Headline(
                title="US equities drift higher as Treasury yields cool",
                source="mock-news",
                published_at=now,
                symbols=["SPY", "SPX"],
            ),
            Headline(
                title="Fed officials reiterate data-dependent policy path",
                source="mock-news",
                published_at=now,
                symbols=["SPY", "FOMC"],
            ),
            Headline(
                title="Energy prices jump on geopolitical tensions",
                source="mock-news",
                published_at=now,
                symbols=["macro"],
            ),
        ]
        return canned[:limit]


class NewsApiProvider(NewsProvider):
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def latest_headlines(self, topics: list[str], limit: int = 12) -> list[Headline]:
        query = " OR ".join(topics)
        response = requests.get(
            f"{self.base_url}/everything",
            params={"q": query, "language": "en", "pageSize": limit, "sortBy": "publishedAt"},
            headers={"X-Api-Key": self.api_key},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        headlines: list[Headline] = []
        for article in articles:
            published = article.get("publishedAt") or datetime.now(UTC).isoformat()
            headlines.append(
                Headline(
                    title=article.get("title", ""),
                    source=(article.get("source") or {}).get("name", "unknown"),
                    published_at=datetime.fromisoformat(published.replace("Z", "+00:00")),
                    url=article.get("url"),
                )
            )
        return headlines
