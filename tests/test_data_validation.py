import pandas as pd

from data.data_store import DataStore


def test_missing_candles_detection():
    idx = pd.to_datetime([
        "2024-01-01 09:30",
        "2024-01-01 09:31",
        "2024-01-01 09:33",
    ])
    bars = pd.DataFrame(
        {
            "open": [1, 2, 3],
            "high": [1.1, 2.1, 3.1],
            "low": [0.9, 1.9, 2.9],
            "close": [1, 2, 3],
            "volume": [100, 100, 100],
        },
        index=idx,
    )
    store = DataStore()
    missing = store.missing_candles(bars, timeframe="1 min")
    assert len(missing) == 1


def test_validate_dataset_flags_issues():
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    bars = pd.DataFrame(
        {
            "open": [1, 2],
            "high": [0.5, 2],
            "low": [1, 1.5],
            "close": [1, 2],
            "volume": [100, 100],
        },
        index=idx,
    )
    store = DataStore()
    report = store.validate_dataset(bars, timeframe="1 day")
    assert not report["valid"]
    assert "high_below_low" in report["issues"]
