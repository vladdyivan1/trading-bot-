"""Classify market regime from technical alert fields."""
from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import MarketRegime


def classify_regime(alert: TradingViewAlert, atr_pct: float | None = None) -> MarketRegime:
    if alert.volume_state == "spike" and alert.atr and alert.price:
        atr_ratio = alert.atr / alert.price
        if atr_ratio > 0.008:
            return MarketRegime.HIGH_VOL

    if alert.ema_fast and alert.ema_slow and alert.price:
        spread = abs(alert.ema_fast - alert.ema_slow) / alert.price
        aligned = (alert.is_bullish and alert.ema_fast > alert.ema_slow) or (
            alert.is_bearish and alert.ema_fast < alert.ema_slow
        )
        if aligned and spread > 0.001:
            return MarketRegime.TREND
        if spread < 0.0003:
            return MarketRegime.CHOP

    if alert.macd_state == "neutral" and alert.volume_state != "spike":
        return MarketRegime.CHOP

    return MarketRegime.TREND
