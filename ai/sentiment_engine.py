"""Rule-based headline sentiment and event-risk scoring."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai.news_providers import NewsHeadline

BULLISH_TERMS = {
    "rally",
    "gain",
    "gains",
    "risk-on",
    "soft landing",
    "lower yields",
    "yields edge lower",
    "dovish",
    "cooling inflation",
    "beat estimates",
    "tech leads",
    "lead premarket gains",
}
BEARISH_TERMS = {
    "selloff",
    "slump",
    "risk-off",
    "higher yields",
    "yields jump",
    "hawkish",
    "hot inflation",
    "miss estimates",
    "geopolitical",
    "default risk",
    "bank stress",
}
EVENT_RISK_TERMS = {
    "fomc",
    "federal reserve",
    "fed",
    "powell",
    "cpi",
    "jobs",
    "unemployment",
    "nonfarm",
    "payrolls",
    "treasury refunding",
    "geopolitical",
    "war",
}


class HeadlineScore(BaseModel):
    title: str
    score: float
    labels: list[str] = Field(default_factory=list)


class NewsAnalysis(BaseModel):
    sentiment: str
    summary: str
    risk_flags: list[str] = Field(default_factory=list)
    headline_scores: list[HeadlineScore] = Field(default_factory=list)


class SentimentEngine:
    """Convert headlines into directional macro support and uncertainty flags."""

    def analyze(self, headlines: list[NewsHeadline]) -> NewsAnalysis:
        if not headlines:
            return NewsAnalysis(
                sentiment="NEUTRAL",
                summary="No recent headlines available; falling back to technical-only mode with lower confidence.",
                risk_flags=["NO_NEWS_AVAILABLE"],
            )

        scored: list[HeadlineScore] = []
        total = 0.0
        event_risk = False
        bullish_hits = 0
        bearish_hits = 0
        for headline in headlines:
            title = headline.title
            lower = title.lower()
            score = 0.0
            labels: list[str] = []
            if any(term in lower for term in BULLISH_TERMS):
                score += 1.0
                bullish_hits += 1
                labels.append("BULLISH")
            if any(term in lower for term in BEARISH_TERMS):
                score -= 1.0
                bearish_hits += 1
                labels.append("BEARISH")
            if any(term in lower for term in EVENT_RISK_TERMS):
                event_risk = True
                labels.append("EVENT_RISK")
            if not labels:
                labels.append("NEUTRAL")
            total += score
            scored.append(HeadlineScore(title=title, score=score, labels=labels))

        risk_flags: list[str] = []
        if event_risk:
            risk_flags.append("EVENT_RISK_HEADLINES")
        if bullish_hits and bearish_hits:
            risk_flags.append("MIXED_HEADLINE_FLOW")
            sentiment = "MIXED"
        elif total > 0.5:
            sentiment = "BULLISH"
        elif total < -0.5:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"

        if sentiment == "MIXED":
            stance = "mixed and less supportive of aggressive scalps"
        elif sentiment == "BULLISH":
            stance = "risk-on/bullish for index calls"
        elif sentiment == "BEARISH":
            stance = "risk-off/bearish for index puts"
        else:
            stance = "neutral and not a strong directional filter"

        summary = f"Latest headline flow is {stance}; decision confidence should remain probabilistic."
        return NewsAnalysis(
            sentiment=sentiment,
            summary=summary,
            risk_flags=risk_flags,
            headline_scores=scored,
        )
