"""Paper trading simulator for options scalping."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from backend.config import Settings, get_settings
from backend.schemas.alerts import Decision, Direction
from backend.services.options_selector import OptionContract

logger = logging.getLogger(__name__)

_positions: dict[str, dict] = {}


class PaperExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings

    def execute(
        self,
        alert_id: str,
        contract: OptionContract,
        direction: Direction,
        quantity: int,
        decision: Decision,
    ) -> dict[str, Any]:
        fill = contract.ask  # buy at ask for realism
        pos_id = str(uuid.uuid4())[:8]
        _positions[pos_id] = {
            "id": pos_id,
            "alert_id": alert_id,
            "contract": contract.symbol,
            "type": contract.contract_type,
            "strike": contract.strike,
            "expiration": str(contract.expiration),
            "quantity": quantity,
            "entry_price": fill,
            "opened_at": datetime.utcnow().isoformat(),
            "max_hold_until": (
                datetime.utcnow() + timedelta(minutes=self.settings.max_hold_minutes)
            ).isoformat(),
            "status": "OPEN",
        }
        logger.info("Paper fill %s x%d @ %.2f", contract.symbol, quantity, fill)
        return {
            "mode": "paper",
            "order_id": pos_id,
            "fill_price": fill,
            "contract": contract.symbol,
            "quantity": quantity,
            "direction": direction.value,
            "decision": decision.value,
            "pnl": 0.0,
        }

    def close_position(self, pos_id: str, exit_price: float, reason: str) -> dict[str, Any]:
        pos = _positions.get(pos_id)
        if not pos:
            return {"success": False, "message": "Position not found"}
        entry = pos["entry_price"]
        qty = pos["quantity"]
        pnl = (exit_price - entry) * qty * 100
        pos["status"] = "CLOSED"
        pos["exit_price"] = exit_price
        pos["pnl"] = pnl
        pos["exit_reason"] = reason
        return {"success": True, "pnl": pnl, "position": pos}

    def get_open_positions(self) -> list[dict]:
        return [p for p in _positions.values() if p.get("status") == "OPEN"]

    def check_exits(self) -> list[dict]:
        """Scale-out / hard stop / max hold time."""
        results = []
        now = datetime.utcnow()
        for pos_id, pos in list(_positions.items()):
            if pos.get("status") != "OPEN":
                continue
            max_hold = datetime.fromisoformat(pos["max_hold_until"])
            if now >= max_hold:
                results.append(self.close_position(pos_id, pos["entry_price"] * 0.95, "MAX_HOLD_TIME"))
        return results


def get_executor(settings: Optional[Settings] = None) -> PaperExecutor:
    return PaperExecutor(settings or get_settings())
