"""Interactive Brokers client wrapper using ib_insync."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd
from ib_insync import IB, util
from loguru import logger

from broker.account import count_open_positions, get_account_summary, get_positions
from broker.contracts import (
    TIMEFRAME_TO_BAR_SIZE,
    TIMEFRAME_TO_DURATION,
    create_contract,
)
from broker.orders import create_limit_order, create_market_order
from config.settings import get_settings
from schemas import AssetClass


class IBKRClient:
    """IBKR connection manager with paper trading defaults."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ib = IB()
        self._event_handlers: list[Callable] = []
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self.ib.isConnected()

    def connect(self) -> bool:
        """Connect to IB Gateway or TWS."""
        if self.is_connected:
            return True
        port = self.settings.ibkr_port
        if self.settings.ibkr_paper and port == 7496:
            logger.warning("Port 7496 is live; switching to paper port 7497")
            port = 7497
        try:
            self.ib.connect(
                self.settings.ibkr_host,
                port,
                clientId=self.settings.ibkr_client_id,
                readonly=False,
            )
            self._setup_event_logging()
            self._connected = True
            logger.info(
                "Connected to IBKR at {}:{} (paper={})",
                self.settings.ibkr_host,
                port,
                self.settings.ibkr_paper,
            )
            return True
        except Exception as e:
            logger.error("IBKR connection failed: {}", e)
            return False

    def disconnect(self) -> None:
        if self.is_connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IBKR")

    def _setup_event_logging(self) -> None:
        def on_error(reqId, errorCode, errorString, contract):
            logger.warning("IBKR error {}: {} (reqId={})", errorCode, errorString, reqId)

        def on_order_status(trade):
            logger.info(
                "Order status: {} {} {} @ {}",
                trade.order.orderId,
                trade.orderStatus.status,
                trade.order.totalQuantity,
                trade.orderStatus.avgFillPrice,
            )

        self.ib.errorEvent += on_error
        self.ib.orderStatusEvent += on_order_status

    def qualify_contract(self, symbol: str, asset_class: AssetClass, **kwargs) -> Any:
        contract = create_contract(symbol, asset_class, **kwargs)
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract: {symbol} ({asset_class})")
        return qualified[0]

    def get_historical_bars(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str,
        duration: Optional[str] = None,
        end_datetime: str = "",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> pd.DataFrame:
        """Pull historical OHLCV bars from IBKR."""
        contract = self.qualify_contract(
            symbol, asset_class, exchange=exchange, currency=currency
        )
        bar_size = TIMEFRAME_TO_BAR_SIZE.get(timeframe, "5 mins")
        dur = duration or TIMEFRAME_TO_DURATION.get(timeframe, "1 Y")

        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime=end_datetime,
            durationStr=dur,
            barSizeSetting=bar_size,
            whatToShow="MIDPOINT" if asset_class == AssetClass.CASH else "TRADES",
            useRTH=asset_class != AssetClass.CASH,
            formatDate=1,
        )
        if not bars:
            return pd.DataFrame()
        df = util.df(bars)
        if "date" in df.columns:
            df.set_index("date", inplace=True)
        df.index = pd.to_datetime(df.index)
        df.rename(
            columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            },
            inplace=True,
        )
        return df[["open", "high", "low", "close", "volume"]]

    def place_order(
        self,
        symbol: str,
        asset_class: AssetClass,
        action: str,
        quantity: float,
        order_type: str = "MKT",
        limit_price: Optional[float] = None,
    ) -> Any:
        """Place order — blocked if live trading disabled."""
        if not self.settings.paper_trading_enabled and not self.settings.live_trading_enabled:
            raise RuntimeError("Trading is disabled in configuration")
        if self.settings.live_trading_enabled and not self.settings.ibkr_paper:
            if not self.settings.live_trading_enabled:
                raise RuntimeError("Live trading requires explicit LIVE_TRADING_ENABLED=true")

        contract = self.qualify_contract(symbol, asset_class)
        if order_type == "MKT":
            order = create_market_order(action, quantity)
        elif order_type == "LMT" and limit_price:
            order = create_limit_order(action, quantity, limit_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        trade = self.ib.placeOrder(contract, order)
        logger.info("Placed {} {} {} x {}", order_type, action, symbol, quantity)
        return trade

    def cancel_order(self, order_id: int) -> None:
        for trade in self.ib.openTrades():
            if trade.order.orderId == order_id:
                self.ib.cancelOrder(trade.order)
                logger.info("Cancelled order {}", order_id)
                return
        logger.warning("Order {} not found for cancellation", order_id)

    def get_order_status(self, order_id: int) -> Optional[dict]:
        for trade in self.ib.trades():
            if trade.order.orderId == order_id:
                return {
                    "order_id": order_id,
                    "status": trade.orderStatus.status,
                    "filled": trade.orderStatus.filled,
                    "avg_fill_price": trade.orderStatus.avgFillPrice,
                    "commission": sum(
                        f.commission for f in trade.fills if f.commissionReport
                    ),
                }
        return None

    def account_summary(self) -> dict:
        return get_account_summary(self.ib)

    def positions(self) -> list[dict]:
        return get_positions(self.ib)

    def open_position_count(self) -> int:
        return count_open_positions(self.ib)
