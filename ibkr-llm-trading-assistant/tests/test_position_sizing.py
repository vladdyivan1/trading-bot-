"""Tests for position sizing."""

from schemas import AssetClass, Direction, TradeSignal, Timeframe
from risk.position_sizing import calculate_position_size


def test_basic_sizing():
    signal = TradeSignal(
        symbol="SPY",
        asset_class=AssetClass.STK,
        timeframe=Timeframe.M5,
        direction=Direction.LONG,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=102.0,
        confidence_score=0.7,
    )
    qty = calculate_position_size(100_000, signal, risk_per_trade_pct=0.5, max_contracts=1000)
    # Risk $500 on $1/share risk = 500 shares, capped at 1000
    assert qty == 500


def test_zero_risk_returns_zero():
    signal = TradeSignal(
        symbol="SPY",
        asset_class=AssetClass.STK,
        timeframe=Timeframe.M5,
        direction=Direction.LONG,
        entry_price=100.0,
        stop_loss=100.0,
        take_profit=105.0,
        confidence_score=0.7,
    )
    assert calculate_position_size(100_000, signal, 0.5, 1000) == 0.0
