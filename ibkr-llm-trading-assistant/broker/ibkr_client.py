"""Interactive Brokers client using ib_insync."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from ib_insync import IB, Order, Trade, util
from loguru import logger

from broker.account import get_account_summary, get_net_liquidation, get_positions_df
from broker.contracts import build_contract, qualify_contract
from config.settings import Settings, get_settings


class IBKRClient:
    """Wrapper around ib_insync for connection and market operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.ib = IB()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self.ib.isConnected()

    def connect(self) -> bool:
        """Connect to IB Gateway or TWS."""
        if self.is_connected:
            return True
        try:
            self.ib.connect(
                self.settings.ibkr_host,
                self.settings.ibkr_port,
                clientId=self.settings.ibkr_client_id,
                readonly=False,
            )
            self._connected = True
            self.ib.orderStatusEvent += self._on_order_status
            self.ib.errorEvent += self._on_error
            mode = "paper" if self.settings.paper_trading else "live"
            logger.info(
                "Connected to IBKR at {}:{} ({})",
                self.settings.ibkr_host,
                self.settings.ibkr_port,
                mode,
            )
            return True
        except Exception as exc:
            logger.error("IBKR connection failed: {}", exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self.is_connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IBKR")

    def _on_order_status(self, trade: Trade) -> None:
        logger.info(
            "Order status: {} {} {} @ {}",
            trade.order.orderId,
            trade.order.action,
            trade.orderStatus.status,
            trade.orderStatus.filled,
        )

    def _on_error(self, req_id: int, error_code: int, error_string: str, contract: Any) -> None:
        logger.warning("IBKR error {} ({}): {}", error_code, req_id, error_string)

    async def qualify(
        self,
        symbol: str,
        asset_class: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        **kwargs,
    ):
        contract = build_contract(symbol, asset_class, exchange, currency, **kwargs)
        return await qualify_contract(self.ib, contract)

    def get_historical_bars(
        self,
        contract,
        duration: str = "1 Y",
        bar_size: str = "1 day",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ) -> pd.DataFrame:
        """Pull historical OHLCV from IBKR."""
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
        )
        if not bars:
            return pd.DataFrame()
        df = util.df(bars)
        if "date" in df.columns:
            df = df.rename(columns={"date": "bar_time"})
            df["bar_time"] = pd.to_datetime(df["bar_time"])
            df = df.set_index("bar_time")
        return df

    def place_order(self, contract, order: Order) -> Trade:
        """Place an order — blocked if live trading disabled and not paper."""
        if not self.settings.paper_trading and not self.settings.live_trading_enabled:
            raise PermissionError(
                "Live trading is disabled. Set LIVE_TRADING_ENABLED=true to allow."
            )
        if self.settings.kill_switch:
            raise PermissionError("Kill switch is active. All trading halted.")
        trade = self.ib.placeOrder(contract, order)
        logger.info("Placed order {} {}", order.action, order.totalQuantity)
        return trade

    def cancel_order(self, order: Order) -> None:
        self.ib.cancelOrder(order)
        logger.info("Cancelled order {}", order.orderId)

    def get_open_trades(self) -> list[Trade]:
        return list(self.ib.openTrades())

    def account_summary(self) -> dict[str, str]:
        return get_account_summary(self.ib, self.settings.ibkr_account or None)

    def net_liquidation(self) -> float:
        return get_net_liquidation(self.ib, self.settings.ibkr_account or None)

    def positions(self) -> pd.DataFrame:
        return get_positions_df(self.ib)
