"""Paper trading execution via IBKR."""

from __future__ import annotations

import json
from typing import Optional

from loguru import logger

from broker.ibkr_client import IBKRClient
from broker.orders import signal_to_order_side
from database.db import get_db_session
from database.repositories import TradeRepository
from risk.risk_manager import RiskManager
from schemas import TradeSignal


class PaperTrader:
    """Places paper trades through IBKR."""

    def __init__(self, client: IBKRClient, risk_manager: RiskManager):
        self.client = client
        self.risk = risk_manager

    def execute(self, signal: TradeSignal, quantity: float) -> dict:
        if not self.client.is_connected:
            if not self.client.connect():
                return {"executed": False, "reason": "IBKR not connected"}

        action = signal_to_order_side(signal.direction, is_entry=True)
        try:
            trade = self.client.place_order(
                signal.symbol,
                signal.asset_class,
                action,
                quantity,
                order_type="LMT",
                limit_price=signal.entry_price,
            )
            order_id = str(trade.order.orderId) if trade else "unknown"
            with get_db_session() as session:
                TradeRepository(session).log_trade(
                    order_id=order_id,
                    symbol=signal.symbol,
                    asset_class=signal.asset_class.value,
                    direction=signal.direction.value,
                    quantity=quantity,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    status="submitted",
                    strategy_name=signal.strategy_name,
                    is_paper=True,
                    signal_json=signal.model_dump_json(),
                )
            logger.info("Paper trade submitted: {} {} x {}", action, signal.symbol, quantity)
            return {
                "executed": True,
                "order_id": order_id,
                "symbol": signal.symbol,
                "quantity": quantity,
                "is_paper": True,
            }
        except Exception as e:
            logger.error("Paper trade failed: {}", e)
            return {"executed": False, "reason": str(e)}
