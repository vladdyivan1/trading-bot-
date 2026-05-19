"""Options contract selection for SPY 0DTE/1DTE scalping."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from backend.config import Settings
from backend.schemas.alerts import Direction


@dataclass
class OptionContract:
    symbol: str
    underlying: str
    contract_type: str
    strike: float
    expiration: date
    dte: int
    delta: float
    bid: float
    ask: float
    open_interest: int
    volume: int

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self) -> float:
        if self.mid <= 0:
            return 1.0
        return (self.ask - self.bid) / self.mid


class OptionsSelector:
    """Select nearest 0DTE/1DTE contract with delta and liquidity filters."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def select(
        self,
        direction: Direction,
        underlying_price: float,
        chain: Optional[list[OptionContract]] = None,
    ) -> tuple[Optional[OptionContract], str]:
        if direction == Direction.NONE:
            return None, "NO_DIRECTION"

        chain = chain or self._mock_chain(underlying_price, direction)
        candidates = [
            c
            for c in chain
            if c.dte == self.settings.default_dte
            or (self.settings.allow_1dte_fallback and c.dte == 1)
        ]
        if not candidates and self.settings.allow_1dte_fallback:
            candidates = [c for c in chain if c.dte <= 1]

        typed = "CALL" if direction == Direction.CALL else "PUT"
        typed_candidates = [c for c in candidates if c.contract_type == typed]

        for c in typed_candidates:
            if not (self.settings.delta_min <= abs(c.delta) <= self.settings.delta_max):
                continue
            if c.open_interest < self.settings.min_open_interest:
                continue
            if c.volume < self.settings.min_option_volume:
                continue
            if c.spread_pct > self.settings.max_spread_pct:
                continue
            return c, ""

        if typed_candidates:
            best = min(typed_candidates, key=lambda x: x.spread_pct)
            if best.spread_pct > self.settings.max_spread_pct:
                return None, "SPREAD_TOO_WIDE"
        return None, "NO_SUITABLE_CONTRACT"

    def _mock_chain(self, price: float, direction: Direction) -> list[OptionContract]:
        """Synthetic chain for paper trading / offline dev."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        strikes = [round(price + offset, 0) for offset in (-2, -1, 0, 1, 2)]
        contracts = []
        for exp, dte in [(today, 0), (tomorrow, 1)]:
            for strike in strikes:
                for ctype, delta_sign in [("CALL", 1), ("PUT", -1)]:
                    dist = abs(strike - price)
                    delta = max(0.25, min(0.65, 0.5 - dist * 0.05)) * delta_sign
                    mid = max(0.5, 3.0 - dist * 0.4)
                    spread = 0.05
                    contracts.append(
                        OptionContract(
                            symbol=f"SPY{exp.strftime('%y%m%d')}{ctype[0]}{int(strike)}",
                            underlying="SPY",
                            contract_type=ctype,
                            strike=strike,
                            expiration=exp,
                            dte=dte,
                            delta=delta,
                            bid=mid - spread / 2,
                            ask=mid + spread / 2,
                            open_interest=500,
                            volume=200,
                        )
                    )
        return contracts
