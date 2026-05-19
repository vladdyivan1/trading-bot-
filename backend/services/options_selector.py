"""Options contract selection for SPY 0DTE/1DTE scalping."""
from datetime import date, timedelta

from backend.config import Settings, get_settings
from backend.schemas.decisions import Direction
from backend.schemas.execution import OptionContract
from backend.services.session_service import now_et


class OptionsSelector:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def select_contract(
        self,
        underlying_price: float,
        direction: Direction,
        dte: int | None = None,
    ) -> OptionContract | None:
        if direction == Direction.NONE:
            return None

        dte = dte if dte is not None else self.settings.default_dte
        exp = self._expiration_for_dte(dte)
        if exp is None and self.settings.fallback_dte:
            exp = self._expiration_for_dte(self.settings.fallback_dte)
            dte = self.settings.fallback_dte
        if exp is None:
            return None

        strike = self._strike_for_delta(underlying_price, direction)
        opt_type = "call" if direction == Direction.CALL else "put"
        symbol = f"SPY{exp.strftime('%y%m%d')}{'C' if opt_type == 'call' else 'P'}{int(strike * 1000):08d}"[:20]

        # Simulated chain metrics for paper trading
        mid = max(0.05, underlying_price * 0.003)
        spread_pct = 0.08
        bid = mid * (1 - spread_pct / 2)
        ask = mid * (1 + spread_pct / 2)

        contract = OptionContract(
            symbol=f"SPY_{exp.isoformat()}_{strike}_{opt_type}",
            underlying="SPY",
            expiration=exp.isoformat(),
            strike=strike,
            option_type=opt_type,
            delta=self._estimate_delta(underlying_price, strike, opt_type),
            bid=round(bid, 2),
            ask=round(ask, 2),
            open_interest=500,
            volume=200,
            dte=dte,
        )
        return contract

    def validate_contract(self, contract: OptionContract) -> list[str]:
        reasons = []
        if contract.open_interest is not None and contract.open_interest < self.settings.min_open_interest:
            reasons.append("low_open_interest")
        if contract.volume is not None and contract.volume < self.settings.min_option_volume:
            reasons.append("low_option_volume")
        if contract.bid and contract.ask and contract.bid > 0:
            spread = (contract.ask - contract.bid) / ((contract.ask + contract.bid) / 2)
            if spread > self.settings.max_spread_pct:
                reasons.append("spread_too_wide")
        if contract.delta is not None:
            if not (self.settings.target_delta_min <= abs(contract.delta) <= self.settings.target_delta_max):
                reasons.append("delta_out_of_range")
        return reasons

    def _expiration_for_dte(self, dte: int) -> date | None:
        today = now_et().date()
        candidate = today + timedelta(days=dte)
        # Skip weekends
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate

    def _strike_for_delta(self, price: float, direction: Direction) -> float:
        """Near-the-money to slightly ITM."""
        step = 1.0
        if direction == Direction.CALL:
            return round((price - 0.5) / step) * step
        return round((price + 0.5) / step) * step

    def _estimate_delta(self, price: float, strike: float, opt_type: str) -> float:
        moneyness = (price - strike) / price
        if opt_type == "call":
            return min(0.85, max(0.25, 0.5 + moneyness * 5))
        return min(-0.25, max(-0.85, -0.5 + moneyness * 5))
