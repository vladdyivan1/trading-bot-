"""News provider abstractions with a deterministic mock provider for local use."""

from __future__ import annotations

import email.utils
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)


class NewsHeadline(BaseModel):
    title: str
    source: str = "mock"
    url: HttpUrl | None = None
    published_at: datetime


class NewsProvider(Protocol):
    def latest_headlines(self, query_terms: list[str], limit: int = 25) -> list[NewsHeadline]:
        ...


class MockNewsProvider:
    """Offline provider used by default and in tests."""

    def latest_headlines(self, query_terms: list[str], limit: int = 25) -> list[NewsHeadline]:
        now = datetime.now(timezone.utc)
        headlines = [
            "S&P 500 futures steady as traders wait for Federal Reserve speakers",
            "Treasury yields edge lower while mega-cap technology shares lead premarket gains",
            "SPY volume mixed ahead of intraday economic calendar",
        ]
        return [
            NewsHeadline(title=title, source="mock", published_at=now)
            for title in headlines[:limit]
        ]


class RssNewsProvider:
    """Simple RSS reader for deployments that supply public market-news feeds."""

    def __init__(self, rss_urls: list[str]) -> None:
        self.rss_urls = rss_urls

    def latest_headlines(self, query_terms: list[str], limit: int = 25) -> list[NewsHeadline]:
        terms = [term.lower() for term in query_terms]
        headlines: list[NewsHeadline] = []
        for url in self.rss_urls:
            try:
                with urllib.request.urlopen(url, timeout=2.5) as response:
                    xml_text = response.read()
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("RSS fetch failed for %s: %s", url, exc)
                continue
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError:
                logger.warning("RSS parse failed for %s", url)
                continue
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                if not title:
                    continue
                if terms and not any(term in title.lower() for term in terms):
                    continue
                published = item.findtext("pubDate")
                published_at = datetime.now(timezone.utc)
                if published:
                    try:
                        parsed = email.utils.parsedate_to_datetime(published)
                        published_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError):
                        pass
                link = item.findtext("link")
                headlines.append(
                    NewsHeadline(
                        title=title,
                        source=url,
                        url=link if link else None,
                        published_at=published_at,
                    )
                )
                if len(headlines) >= limit:
                    return headlines
        return headlines


def build_news_provider(provider: str, rss_urls: list[str]) -> NewsProvider:
    if provider == "rss" and rss_urls:
        return RssNewsProvider(rss_urls)
    return MockNewsProvider()
