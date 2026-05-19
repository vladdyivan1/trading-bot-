"""Data validation tests."""

import pandas as pd

from data.historical_data import HistoricalDataService


def test_validate_gaps_daily(sample_ohlcv: pd.DataFrame) -> None:
    svc = HistoricalDataService()
    gaps = svc.validate_gaps(sample_ohlcv, "1 day")
    assert isinstance(gaps, list)
