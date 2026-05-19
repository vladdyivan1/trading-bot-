from ai.sentiment_engine import aggregate_sentiment, detect_event_risk, score_headline


def test_score_headline_bullish():
    assert score_headline("S&P 500 rally on strong earnings") > 0


def test_score_headline_bearish():
    assert score_headline("Market selloff amid geopolitical risk") < 0


def test_detect_event_risk():
    headlines = [{"title": "Fed Chair Powell speaks on inflation"}]
    assert detect_event_risk(headlines) is True


def test_aggregate_sentiment_mixed():
    headlines = [
        {"title": "Rally in tech", "score": 0.5},
        {"title": "Selloff in energy", "score": -0.5},
    ]
    sentiment, _ = aggregate_sentiment(headlines)
    assert sentiment == "MIXED"
