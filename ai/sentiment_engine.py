"""Rule-based sentiment scoring for headlines."""
import re

BULLISH_KEYWORDS = [
    "rally", "surge", "gain", "beats", "strong", "risk-on", "eases", "cuts rates",
    "record high", "inflows",
]
BEARISH_KEYWORDS = [
    "selloff", "plunge", "misses", "weak", "risk-off", "hike", "inflation hot",
    "recession", "downgrade", "geopolitical", "war", "default",
]
EVENT_KEYWORDS = [
    "fed", "fomc", "powell", "cpi", "ppi", "jobs report", "nonfarm", "unemployment",
    "treasury auction", "earnings", "gdp", "pce",
]


def score_headline(title: str) -> float:
    t = title.lower()
    score = 0.0
    for w in BULLISH_KEYWORDS:
        if w in t:
            score += 0.15
    for w in BEARISH_KEYWORDS:
        if w in t:
            score -= 0.15
    return max(-1.0, min(1.0, score))


def detect_event_risk(headlines: list[dict]) -> bool:
    for h in headlines:
        t = h.get("title", "").lower()
        if any(k in t for k in EVENT_KEYWORDS):
            return True
    return False


def aggregate_sentiment(headlines: list[dict]) -> tuple[str, float]:
    if not headlines:
        return "NEUTRAL", 0.0

    scores = []
    for h in headlines:
        if "score" in h and h["score"] != 0:
            scores.append(float(h["score"]))
        else:
            scores.append(score_headline(h.get("title", "")))

    avg = sum(scores) / len(scores)
    if avg > 0.2:
        return "BULLISH", avg
    if avg < -0.2:
        return "BEARISH", avg
    if max(scores) > 0.15 and min(scores) < -0.15:
        return "MIXED", avg
    return "NEUTRAL", avg


def macro_contradiction(technical_bull: bool, technical_bear: bool, sentiment: str) -> bool:
    if technical_bull and sentiment == "BEARISH":
        return True
    if technical_bear and sentiment == "BULLISH":
        return True
    return False
