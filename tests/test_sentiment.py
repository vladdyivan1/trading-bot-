from ai.sentiment_engine import aggregate_sentiment, detect_event_risk, score_headline


def test_score_headline_bullish():
    assert score_headline("Markets rally on strong earnings beat") > 0


def test_score_headline_bearish():
    assert score_headline("Stocks plunge on hawkish Fed rate hike fears") < 0


def test_event_risk_detection():
    flags = detect_event_risk(["Fed Chair Powell speaks ahead of FOMC", "SPY steady"])
    assert "FED_SPEECH" in flags or "FOMC" in flags


def test_aggregate_mixed():
    assert aggregate_sentiment([0.5, -0.5]) == "MIXED"
