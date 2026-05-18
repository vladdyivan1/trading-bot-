"""Interactive Brokers client wrapper using ib_insync."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from loguru import logger

from broker.account import parse_account_summary
from broker.contracts import ContractSpec, build_contract
from broker.orders import OrderRequest, build_order
from config.settings import settings
from data.market_data import MarketQuote

try:
    from ib_insync import IB, Trade, util
except ImportError:  # pragma: no cover
    IB = None  # type: ignore[assignment]
    Trade = object  # type: ignore[assignment]
    util = None  # type: ignore[assignment]


class IBKRClient:
    """Safety-first IBKR client. Defaults to paper trading."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        readonly: bool = False,
    ) -> None:
        if IB is None:
            raise RuntimeError("ib_insync is required to use IBKRClient")
        self.host = host or settings.ibkr_host
        self.port = port or settings.ibkr_port
        self.client_id = client_id or settings.ibkr_client_id
        self.readonly = readonly
        self.ib = IB()
        self._wire_events()

    @property
    def is_connected(self) -> bool:
        return bool(self.ib.isConnected())

    def connect(self) -> None:
        logger.info("Connecting to IBKR {}:{} client_id={}", self.host, self.port, self.client_id)
        self.ib.connect(self.host, self.port, clientId=self.client_id, readonly=self.readonly)
        logger.info("IBKR connected={}", self.is_connected)

    def disconnect(self) -> None:
        if self.is_connected:
            self.ib.disconnect()
            logger.info("IBKR disconnected")

    def account_summary(self) -> dict[str, str]:
        return parse_account_summary(self.ib.accountSummary())

    def open_positions(self) -> list[dict[str, Any]]:
        positions = []
        for pos in self.ib.positions():
            positions.append(
                {
                    "account": pos.account,
                    "symbol": getattr(pos.contract, "symbol", ""),
                    "secType": getattr(pos.contract, "secType", ""),
                    "position": float(pos.position),
                    "avgCost": float(pos.avgCost),
                }
            )
        return positions

    def qualify_contract(
        self,
        symbol: str,
        asset_class: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        **kwargs: Any,
    ) -> Any:
        contract = build_contract(
            ContractSpec(symbol=symbol, asset_class=asset_class, exchange=exchange, currency=currency, **kwargs)
        )
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"Unable to qualify contract for {symbol} {asset_class}")
        return qualified[0]

    def fetch_historical_bars(
        self,
        symbol: str,
        asset_class: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        duration: str = "5 Y",
        bar_size: str = "1 day",
        end_datetime: datetime | None = None,
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        **contract_kwargs: Any,
    ) -> pd.DataFrame:
        contract = self.qualify_contract(symbol, asset_class, exchange, currency, **contract_kwargs)
        if asset_class.upper() == "CASH":
            what_to_show = "MIDPOINT"
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime=end_datetime or "",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=False,
        )
        df = util.df(bars)
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()

    def get_quote(
        self,
        symbol: str,
        asset_class: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        **contract_kwargs: Any,
    ) -> MarketQuote:
        contract = self.qualify_contract(symbol, asset_class, exchange, currency, **contract_kwargs)
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(2)
        self.ib.cancelMktData(contract)
        return MarketQuote(symbol=symbol, bid=ticker.bid, ask=ticker.ask, last=ticker.last)

    def place_order(
        self,
        symbol: str,
        asset_class: str,
        order_request: OrderRequest,
        exchange: str = "SMART",
        currency: str = "USD",
        **contract_kwargs: Any,
    ) -> Trade:
        if settings.trading_mode == "live" and not settings.live_trading_allowed:
            raise PermissionError("Live trading is disabled by configuration")
        contract = self.qualify_contract(symbol, asset_class, exchange, currency, **contract_kwargs)
        order = build_order(order_request)
        trade = self.ib.placeOrder(contract, order)
        logger.info("Placed {} {} {} order_id={}", order.action, order.totalQuantity, symbol, trade.order.orderId)
        return trade

    def cancel_order(self, trade: Trade) -> None:
        self.ib.cancelOrder(trade.order)
        logger.info("Cancelled order_id={}", trade.order.orderId)

    def order_status(self, trade: Trade) -> dict[str, Any]:
        status = trade.orderStatus
        return {
            "order_id": trade.order.orderId,
            "status": status.status,
            "filled": status.filled,
            "remaining": status.remaining,
            "avg_fill_price": status.avgFillPrice,
        }

    def _wire_events(self) -> None:
        self.ib.errorEvent += lambda req_id, code, msg, contract: logger.warning(
            "IBKR error req_id={} code={} msg={} contract={}", req_id, code, msg, contract
        )
        self.ib.disconnectedEvent += lambda: logger.warning("IBKR disconnected event")
        self.ib.connectedEvent += lambda: logger.info("IBKR connected event")
