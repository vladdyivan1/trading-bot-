from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from random import uniform
from typing import Any

from backend.schemas.decision import OptionDirection
from execution.broker_base import ExecutionAdapter, ExecutionRequest, ExecutionResult, OptionContractCandidate


class PaperExecutionAdapter(ExecutionAdapter):
    def __init__(self) -> None:
        self._positions: list[dict[str, Any]] = []

    def _build_contract_chain(self, request: ExecutionRequest) -> list[OptionContractCandidate]:
        base_exp = date.today() + timedelta(days=request.dte_preference)
        fallback_exp = date.today() + timedelta(days=request.dte_fallback)
        strikes = [
            round(request.underlying_price - 2, 0),
            round(request.underlying_price - 1, 0),
            round(request.underlying_price, 0),
            round(request.underlying_price + 1, 0),
            round(request.underlying_price + 2, 0),
        ]
        expirations = [base_exp, fallback_exp]
        contracts: list[OptionContractCandidate] = []
        for exp in expirations:
            for strike in strikes:
                directional_delta = 0.42 if request.direction == OptionDirection.CALL else -0.42
                delta = directional_delta + uniform(-0.12, 0.12)
                bid = max(0.4, abs(request.underlying_price - strike) * 0.25 + uniform(0.4, 1.4))
                ask = bid * (1 + uniform(0.03, 0.16))
                contracts.append(
                    OptionContractCandidate(
                        symbol=f"{request.underlying_symbol}_{exp:%Y%m%d}_{'C' if request.direction == OptionDirection.CALL else 'P'}_{int(strike*1000)}",
                        expiration=exp,
                        strike=strike,
                        delta=delta,
                        bid=bid,
                        ask=ask,
                        open_interest=250,
                        volume=450,
                    )
                )
        return contracts

    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        chain = self._build_contract_chain(request)
        filtered = [
            c
            for c in chain
            if request.delta_min <= abs(c.delta) <= request.delta_max
            and c.open_interest >= request.min_open_interest
            and c.volume >= request.min_volume
            and c.spread_pct <= request.max_spread_pct
        ]
        if not filtered:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                reason="No option contracts met delta/liquidity/spread constraints.",
            )
        selected = sorted(
            filtered,
            key=lambda c: (c.expiration, abs(c.strike - request.underlying_price), c.spread_pct),
        )[0]
        fill_price = selected.mid_price * (1 + uniform(-0.01, 0.01))
        opened_at = datetime.now(UTC).isoformat()
        self._positions.append(
            {
                "contract_symbol": selected.symbol,
                "direction": request.direction.value,
                "quantity": request.quantity,
                "entry_price": round(fill_price, 4),
                "opened_at": opened_at,
                "max_hold_minutes": request.max_hold_minutes,
                "expiration": selected.expiration.isoformat(),
                "strike": selected.strike,
            }
        )
        return ExecutionResult(
            accepted=True,
            status="OPEN",
            reason="Paper execution simulated.",
            contract_symbol=selected.symbol,
            expiration=selected.expiration.isoformat(),
            strike=selected.strike,
            delta=selected.delta,
            quantity=request.quantity,
            fill_price=round(fill_price, 4),
            spread_pct=round(selected.spread_pct, 4),
            metadata={"selected_contract": asdict(selected)},
        )

    def open_positions(self) -> list[dict[str, Any]]:
        return list(self._positions)
