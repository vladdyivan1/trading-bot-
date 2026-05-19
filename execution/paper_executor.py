"""Paper trading simulator for approved options scalps."""

from __future__ import annotations

import itertools
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import Order, Position
from backend.schemas.decision import ExecutionResult
from execution.broker_base import BrokerAdapter, OrderRequest


class PaperExecutor(BrokerAdapter):
    """Fills approved contracts at quote mid or a conservative synthetic price."""

    _ids = itertools.count(1)

    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        quote = request.contract.quote
        fill_price = quote.mid if quote else max(0.05, round(request.max_price * 0.01, 2))
        order_id = f"PAPER-{next(self._ids)}"
        return ExecutionResult(
            status="FILLED",
            order_id=order_id,
            symbol=request.contract.symbol,
            quantity=request.quantity,
            fill_price=fill_price,
            message="Paper order filled; live broker execution is disabled by default.",
        )

    def persist_fill(
        self,
        db: Session,
        decision_id: int,
        request: OrderRequest,
        result: ExecutionResult,
    ) -> None:
        now = datetime.now(timezone.utc)
        notional = result.fill_price * result.quantity * 100
        order = Order(
            decision_id=decision_id,
            created_at=now,
            status=result.status,
            symbol=result.symbol or request.contract.symbol,
            side=request.side,
            quantity=result.quantity,
            price=result.fill_price,
            notional=notional,
            realized_pnl=0.0,
            metadata_={"paper": True, **request.metadata},
        )
        position = Position(
            opened_at=now,
            symbol=result.symbol or request.contract.symbol,
            direction=request.contract.right,
            quantity=result.quantity,
            entry_price=result.fill_price,
            status="OPEN",
            metadata_={
                "max_hold_minutes": request.contract.max_hold_minutes,
                "expiration": request.contract.expiration,
                "strike": request.contract.strike,
                **request.metadata,
            },
        )
        db.add(order)
        db.add(position)
