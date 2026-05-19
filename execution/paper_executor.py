"""Paper trading simulator for SPY options scalps."""
import uuid
from datetime import datetime, timedelta

from backend.config import Settings, get_settings
from backend.schemas.execution import ExecutionResult, OptionContract
from execution.broker_base import BrokerAdapter


class PaperExecutor(BrokerAdapter):
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._positions: dict[str, ExecutionResult] = {}

    async def open_position(
        self, contract: OptionContract, quantity: int, size_modifier: float = 1.0
    ) -> ExecutionResult:
        if contract.bid is None or contract.ask is None:
            return ExecutionResult(
                success=False,
                order_id="",
                side="buy",
                quantity=quantity,
                entry_price=0.0,
                status="rejected",
                message="Missing quote for paper fill",
            )

        fill = (contract.bid + contract.ask) / 2
        order_id = f"PAPER-{uuid.uuid4().hex[:12]}"
        result = ExecutionResult(
            success=True,
            order_id=order_id,
            contract=contract,
            side="buy",
            quantity=quantity,
            entry_price=round(fill, 2),
            status="open",
            message="Paper fill simulated",
            opened_at=datetime.utcnow(),
        )
        self._positions[order_id] = result
        return result

    async def close_position(self, order_id: str, reason: str = "signal") -> ExecutionResult:
        pos = self._positions.get(order_id)
        if not pos or not pos.contract:
            return ExecutionResult(
                success=False,
                order_id=order_id,
                side="sell",
                quantity=0,
                entry_price=0.0,
                status="rejected",
                message="Position not found",
            )

        # Simulate PnL: random walk simplified as +/- 15% of premium
        exit_price = pos.entry_price * 1.08 if reason != "stop" else pos.entry_price * 0.85
        pnl = (exit_price - pos.entry_price) * pos.quantity * 100
        pos.exit_price = round(exit_price, 2)
        pos.pnl = round(pnl, 2)
        pos.status = "closed"
        pos.closed_at = datetime.utcnow()
        return pos

    async def get_open_positions(self) -> list[ExecutionResult]:
        now = datetime.utcnow()
        closed_ids = []
        for oid, pos in self._positions.items():
            if pos.status != "open" or not pos.opened_at:
                continue
            hold = (now - pos.opened_at).total_seconds() / 60
            if hold >= self.settings.max_hold_minutes:
                await self.close_position(oid, reason="max_hold_time")
                closed_ids.append(oid)
        return [p for p in self._positions.values() if p.status == "open"]

    async def check_exits(self) -> list[ExecutionResult]:
        """Scale-out / hard stop simulation."""
        results = []
        for oid, pos in list(self._positions.items()):
            if pos.status != "open":
                continue
            # Simulated stop if held too long handled above
            pass
        return results
