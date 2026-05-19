from __future__ import annotations

from backend.schemas.decision import MarketRegime
from backend.schemas.tradingview import TradingViewAlert


class RegimeClassifier:
    def classify(self, alert: TradingViewAlert, risk_flags: list[str]) -> MarketRegime:
        if any(flag.startswith("EVENT:") for flag in risk_flags):
            return MarketRegime.EVENT_RISK
        atr = alert.atr or 0.0
        price = alert.price
        vol_ratio = atr / price if price else 0.0
        if vol_ratio > 0.01:
            return MarketRegime.HIGH_VOL

        ema_fast = alert.ema_fast or price
        ema_slow = alert.ema_slow or price
        separation = abs(ema_fast - ema_slow) / price if price else 0
        if separation > 0.0015 and alert.macd_state and "trend" in alert.macd_state.lower():
            return MarketRegime.TREND
        return MarketRegime.CHOP
