import pandas as pd

from data.data_store import HistoricalDataStore


def test_validate_missing_candles_detects_gap():
    bars = pd.DataFrame(
        {
            "open": [1, 2, 4],
            "high": [1, 2, 4],
            "low": [1, 2, 4],
            "close": [1, 2, 4],
            "volume": [10, 10, 10],
        },
        index=pd.to_datetime(["2024-01-01 09:30", "2024-01-01 09:31", "2024-01-01 09:33"]),
    )

    missing = HistoricalDataStore().validate_missing_candles(bars, "1 min")

    assert pd.Timestamp("2024-01-01 09:32") in missing
