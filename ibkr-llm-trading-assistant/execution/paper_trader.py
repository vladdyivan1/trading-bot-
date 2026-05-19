"""Paper trading execution via IBKR."""

from __future__ import annotations

from loguru import logger

from broker.contracts import build_contract
from broker.ibkr_client import IBKRClient
from broker.orders import build_market_order, direction_to_action
from database.db import get_session
from database.repositories import TradeRepository
from schemas import TradeSignal


class PaperTrader:
    """Execute paper trades through IBKR."""

    def __init__(self, client: IBKRClient | None = None) -> None:
        self.client = client or IBKRClient()

    def execute(self, signal: TradeSignal, quantity: int) -> dict:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if not self.client.settings.paper_trading:
            raise PermissionError("PaperTrader requires paper_trading=true")

        contract = build_contract(
            signal.symbol,
            signal.asset_class,
        )
        qualified = self.client.ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"Cannot qualify {signal.symbol}")
        contract = qualified[0]

        action = direction_to_action(signal.direction, is_entry=True)
        order = build_market_order(action, quantity)
        trade = self.client.place_order(contract, order)

        with get_session() as session:
            repo = TradeRepository(session)
            log = repo.log_trade(
                order_id=str(trade.order.orderId),
                symbol=signal.symbol,
                asset_class=signal.asset_class,
                direction=signal.direction.value,
                quantity=quantity,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status="submitted",
                strategy_name=signal.strategy_name,
                is_paper=True,
            )

        logger.info("Paper order placed: {} {} x{}", action, signal.symbol, quantity)
        return {
            "order_id": trade.order.orderId,
            "trade_log_id": log.id,
            "status": "submitted",
        }
