"""Rule-based and headline-level sentiment scoring."""

import re
from typing import Iterable

BULLISH_WORDS = {
    "rally", "surge", "gain", "beat", "strong", "growth", "risk-on",
    "record high", "easing", "dovish", "cooling inflation",
}
BEARISH_WORDS = {
    "selloff", "plunge", "miss", "weak", "recession", "risk-off",
    "hawkish", "rate hike", "geopolitical", "war", "default", "crisis",
}


def score_headline(title: str) -> float:
    """Return sentiment score in [-1, 1]."""
    t = title.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in t)
    bear = sum(1 for w in BEARISH_WORDS if w in t)
    if bull == bear == 0:
        return 0.0
    return (bull - bear) / max(bull + bear, 1)


def aggregate_sentiment(scores: Iterable[float]) -> str:
    vals = list(scores)
    if not vals:
        return "NEUTRAL"
    avg = sum(vals) / len(vals)
    if avg > 0.2:
        return "BULLISH"
    if avg < -0.2:
        return "BEARISH"
    if max(vals) > 0.3 and min(vals) < -0.3:
        return "MIXED"
    return "NEUTRAL"


def detect_event_risk(texts: Iterable[str]) -> list[str]:
    flags = []
    combined = " ".join(texts).lower()
    patterns = {
        "FOMC": r"\bfomc\b|\bfed meeting\b",
        "CPI": r"\bcpi\b|\binflation (data|report)\b",
        "JOBS": r"\bjobs report\b|\bnonfarm\b|\bunemployment\b",
        "FED_SPEECH": r"\bpowell\b|\bfed chair\b",
        "GEOPOLITICAL": r"\bwar\b|\bgeopolitical\b|\bconflict\b",
    }
    for name, pat in patterns.items():
        if re.search(pat, combined):
            flags.append(name)
    return flags
