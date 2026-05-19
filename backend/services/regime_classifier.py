"""Classify market regime from technical alert fields."""

from backend.schemas.alerts import MarketRegime, TradingViewAlert


def classify_regime(alert: TradingViewAlert) -> MarketRegime:
    atr = alert.atr or 0
    rsi = alert.rsi or 50
    vol_state = (alert.volume_state or "").lower()
    macd = (alert.macd_state or "").lower()

    if vol_state == "spike" and atr > 2:
        return MarketRegime.HIGH_VOL

    if abs(rsi - 50) < 8 and "flat" in macd:
        return MarketRegime.CHOP

    ema_fast = alert.ema_fast or 0
    ema_slow = alert.ema_slow or 0
    if ema_fast and ema_slow and abs(ema_fast - ema_slow) / max(ema_slow, 1) > 0.002:
        return MarketRegime.TREND

    return MarketRegime.CHOP
