"""Options-aware contract selection and liquidity checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.config import Settings


@dataclass(frozen=True)
class OptionQuote:
    bid: float
    ask: float
    delta: float | None = None
    open_interest: int | None = None
    volume: int | None = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self) -> float:
        if self.mid <= 0:
            return 1.0
        return (self.ask - self.bid) / self.mid


@dataclass(frozen=True)
class OptionContract:
    underlying: str
    expiration: str
    strike: float
    right: str
    dte: int
    symbol: str
    max_hold_minutes: int
    quote: OptionQuote | None = None


class OptionsSelector:
    """Selects a near-the-money SPY option contract without requiring live data."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tz = ZoneInfo(settings.market_timezone)

    def select_contract(
        self,
        underlying: str,
        price: float,
        direction: str,
        current_time: datetime | None = None,
        quote: OptionQuote | None = None,
    ) -> OptionContract:
        now_et = (current_time or datetime.now(self.tz)).astimezone(self.tz)
        dte = self.settings.default_dte
        if now_et.strftime("%H:%M") >= self.settings.late_day_cutoff:
            dte = self.settings.fallback_dte
        expiration = (now_et.date() + timedelta(days=dte)).strftime("%Y-%m-%d")
        right = "C" if direction == "CALL" else "P"
        strike = self._near_money_strike(price, direction)
        compact_exp = expiration.replace("-", "")[2:]
        symbol = f"{underlying}{compact_exp}{right}{int(strike * 1000):08d}"
        return OptionContract(
            underlying=underlying,
            expiration=expiration,
            strike=strike,
            right=right,
            dte=dte,
            symbol=symbol,
            max_hold_minutes=self.settings.max_hold_minutes,
            quote=quote,
        )

    def liquidity_rejections(self, quote: OptionQuote | None) -> list[str]:
        if quote is None:
            return []
        rejections: list[str] = []
        if quote.spread_pct > self.settings.max_option_spread_pct:
            rejections.append("OPTION_SPREAD_TOO_WIDE")
        if quote.open_interest is not None and quote.open_interest < self.settings.min_option_open_interest:
            rejections.append("OPTION_OPEN_INTEREST_TOO_LOW")
        if quote.volume is not None and quote.volume < self.settings.min_option_volume:
            rejections.append("OPTION_VOLUME_TOO_LOW")
        if quote.delta is not None and not (
            self.settings.target_delta_min <= abs(quote.delta) <= self.settings.target_delta_max
        ):
            rejections.append("OPTION_DELTA_OUT_OF_RANGE")
        return rejections

    @staticmethod
    def _near_money_strike(price: float, direction: str) -> float:
        rounded = round(price)
        if direction == "CALL":
            return float(min(rounded, int(price)))
        return float(max(rounded, int(price + 0.999)))
