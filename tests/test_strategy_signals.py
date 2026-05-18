import pandas as pd

from strategies.moving_average_strategy import MovingAverageCrossoverStrategy


def test_moving_average_strategy_generates_structured_long_signal():
    data = pd.DataFrame(
        {
            "open": [10, 10, 10, 9, 12],
            "high": [10.5, 10.5, 10.5, 12.5, 13],
            "low": [9.5, 9.5, 9.5, 8.5, 11.5],
            "close": [10, 10, 10, 9, 12],
            "volume": [1000, 1000, 1000, 1200, 2000],
        },
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    strategy = MovingAverageCrossoverStrategy("SPY", fast_window=2, slow_window=3)

    signal = strategy.generate_signal(data)

    assert signal is not None
    assert signal.symbol == "SPY"
    assert signal.direction == "long"
    assert signal.entry_price == 12
    assert signal.stop_loss is not None
    assert signal.take_profit is not None
    assert 0 <= signal.confidence_score <= 1
