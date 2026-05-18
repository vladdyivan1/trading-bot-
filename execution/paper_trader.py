"""Paper-trading adapter that sends validated orders to IBKR."""

from __future__ import annotations

from broker.contracts import ContractSpec
from broker.ibkr_client import IBKRClient
from broker.orders import OrderRequest
from strategies.base_strategy import StrategySignal


class PaperTrader:
    def __init__(self, ibkr_client: IBKRClient) -> None:
        self.ibkr_client = ibkr_client

    def execute_signal(self, signal: StrategySignal, quantity: int) -> dict:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        side = "BUY" if signal.direction == "long" else "SELL"
        contract = ContractSpec(
            symbol=signal.symbol,
            asset_class=signal.asset_class,
            exchange="SMART",
            currency="USD" if signal.asset_class != "FX" else signal.symbol[-3:],
        )
        order = OrderRequest(side=side, quantity=quantity, order_type="MKT")
        return self.ibkr_client.place_order(contract, order)
