from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.schemas.decision import NewsSentiment

from ai.news_providers import Headline


BULLISH_TERMS = {
    "rally",
    "beat",
    "cooling inflation",
    "soft landing",
    "risk-on",
    "stimulus",
    "eases",
    "upgrade",
}
BEARISH_TERMS = {
    "selloff",
    "miss",
    "sticky inflation",
    "risk-off",
    "downgrade",
    "cuts guidance",
    "recession",
    "geopolitical",
}
EVENT_RISK_TERMS = {"fomc", "powell", "cpi", "jobs report", "nfp", "fed decision", "rate decision"}


@dataclass(slots=True)
class SentimentResult:
    sentiment: NewsSentiment
    score: float
    reason_summary: str
    risk_flags: list[str]


class SentimentEngine:
    def score_headline(self, headline: str) -> float:
        lowered = headline.lower()
        score = 0.0
        if any(term in lowered for term in BULLISH_TERMS):
            score += 1.0
        if any(term in lowered for term in BEARISH_TERMS):
            score -= 1.0
        return score

    def detect_risk_flags(self, headline: str) -> list[str]:
        lowered = headline.lower()
        return [f"EVENT:{term.upper()}" for term in EVENT_RISK_TERMS if term in lowered]

    def evaluate(self, headlines: Iterable[Headline]) -> SentimentResult:
        scores: list[float] = []
        risk_flags: list[str] = []
        for item in headlines:
            scores.append(self.score_headline(item.title))
            risk_flags.extend(self.detect_risk_flags(item.title))
        risk_flags = sorted(set(risk_flags))
        net_score = sum(scores)

        if not scores:
            sentiment = NewsSentiment.NEUTRAL
        elif net_score > 1.0:
            sentiment = NewsSentiment.BULLISH
        elif net_score < -1.0:
            sentiment = NewsSentiment.BEARISH
        elif any(score > 0 for score in scores) and any(score < 0 for score in scores):
            sentiment = NewsSentiment.MIXED
        else:
            sentiment = NewsSentiment.NEUTRAL

        summary = "No recent headlines available; fallback to technical-only mode."
        if scores:
            summary = (
                f"Headline sentiment {sentiment.value.lower()} (score={net_score:.2f}) "
                "with probabilistic confidence adjustments."
            )
            if risk_flags:
                summary += f" Event risk flags detected: {', '.join(risk_flags)}."

        return SentimentResult(
            sentiment=sentiment,
            score=net_score,
            reason_summary=summary,
            risk_flags=risk_flags,
        )
