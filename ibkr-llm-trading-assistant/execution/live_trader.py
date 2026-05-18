"""Live trading execution — disabled by default."""

from __future__ import annotations

from loguru import logger

from broker.ibkr_client import IBKRClient
from broker.orders import signal_to_order_side
from config.settings import get_settings
from database.db import get_db_session
from database.repositories import TradeRepository
from risk.risk_manager import RiskManager
from schemas import TradeSignal


class LiveTrader:
    """Live order execution — requires LIVE_TRADING_ENABLED=true."""

    def __init__(self, client: IBKRClient, risk_manager: RiskManager):
        self.client = client
        self.risk = risk_manager
        self.settings = get_settings()

    def execute(self, signal: TradeSignal, quantity: float) -> dict:
        if not self.settings.live_trading_enabled:
            logger.error("Live trading blocked — set LIVE_TRADING_ENABLED=true")
            return {"executed": False, "reason": "Live trading disabled"}

        if self.settings.ibkr_paper:
            logger.warning("Live trader called but IBKR is in paper mode")

        action = signal_to_order_side(signal.direction, is_entry=True)
        trade = self.client.place_order(
            signal.symbol, signal.asset_class, action, quantity, order_type="MKT"
        )
        order_id = str(trade.order.orderId)
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
                is_paper=False,
                signal_json=signal.model_dump_json(),
            )
        return {"executed": True, "order_id": order_id, "is_paper": False}
