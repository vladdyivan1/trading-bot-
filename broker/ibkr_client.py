"""IBKR client wrapper using ib_insync."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from broker.contracts import ContractSpec, QualifiedContract
from broker.orders import OrderRequest, build_order
from config.settings import Settings, get_settings

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


class IBKRClient:
    """Safe wrapper around Interactive Brokers API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._ib = None
        self._trades_by_order_id: dict[int, Any] = {}

    @property
    def ib(self):
        if self._ib is None:
            try:
                from ib_insync import IB
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("Install ib_insync to use IBKR features") from exc
            self._ib = IB()
        return self._ib

    def connect(self) -> bool:
        if self.ib.isConnected():
            return True
        logger.info(
            "Connecting to IBKR {}:{} client_id={}",
            self.settings.ib_host,
            self.settings.ib_port,
            self.settings.ib_client_id,
        )
        self.ib.connect(
            host=self.settings.ib_host,
            port=self.settings.ib_port,
            clientId=self.settings.ib_client_id,
            timeout=10,
        )
        logger.info("IBKR connected={}", self.ib.isConnected())
        return bool(self.ib.isConnected())

    def disconnect(self) -> None:
        if self._ib and self.ib.isConnected():
            self.ib.disconnect()
            logger.info("IBKR disconnected")

    def is_connected(self) -> bool:
        return bool(self._ib and self.ib.isConnected())

    def get_account_summary(self) -> dict[str, str]:
        self._require_connection()
        summary = self.ib.accountSummary(self.settings.ib_account)
        return {entry.tag: entry.value for entry in summary}

    def get_open_positions(self) -> list[dict[str, Any]]:
        self._require_connection()
        positions = self.ib.positions(self.settings.ib_account)
        return [
            {
                "account": p.account,
                "symbol": getattr(p.contract, "symbol", ""),
                "asset_class": getattr(p.contract, "secType", ""),
                "position": float(p.position),
                "avg_cost": float(p.avgCost),
            }
            for p in positions
        ]

    def qualify_contract(self, spec: ContractSpec) -> QualifiedContract:
        self._require_connection()
        contract = spec.to_ib_contract()
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise RuntimeError(f"Unable to qualify contract: {spec.model_dump()}")
        q = qualified[0]
        return QualifiedContract(
            con_id=getattr(q, "conId", 0),
            symbol=getattr(q, "symbol", spec.symbol),
            asset_class=spec.asset_class,
            exchange=getattr(q, "exchange", spec.exchange),
            currency=getattr(q, "currency", spec.currency),
            local_symbol=getattr(q, "localSymbol", None),
        )

    def req_historical_data(
        self,
        spec: ContractSpec,
        end_datetime: datetime | str | None = None,
        duration: str = "1 Y",
        bar_size: str = "1 day",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ) -> pd.DataFrame:
        self._require_connection()
        contract = spec.to_ib_contract()
        self.ib.qualifyContracts(contract)
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime=end_datetime or "",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
        )
        if not bars:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        try:
            from ib_insync import util

            df = util.df(bars)
        except Exception:  # pragma: no cover
            rows = []
            for bar in bars:
                rows.append(
                    {
                        "date": getattr(bar, "date", None),
                        "open": getattr(bar, "open", 0.0),
                        "high": getattr(bar, "high", 0.0),
                        "low": getattr(bar, "low", 0.0),
                        "close": getattr(bar, "close", 0.0),
                        "volume": getattr(bar, "volume", 0.0),
                    }
                )
            df = pd.DataFrame(rows)

        df["date"] = pd.to_datetime(df["date"])
        df = df.rename(columns={"date": "timestamp"}).set_index("timestamp").sort_index()
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                df[col] = 0.0
        return df[["open", "high", "low", "close", "volume"]]

    def place_order(self, spec: ContractSpec, order_request: OrderRequest) -> dict[str, Any]:
        self._require_connection()
        if not self.settings.paper_trading_only and not self.settings.live_trading_enabled:
            raise RuntimeError("Live mode is disabled. Enable explicitly in config.")

        contract = spec.to_ib_contract()
        self.ib.qualifyContracts(contract)
        order = build_order(order_request)
        trade = self.ib.placeOrder(contract, order)
        self._trades_by_order_id[int(order.orderId)] = trade

        self.ib.sleep(0.3)
        status = trade.orderStatus.status if trade.orderStatus else "Submitted"
        fill_price = trade.orderStatus.avgFillPrice if trade.orderStatus else None
        return {
            "order_id": str(order.orderId),
            "status": status,
            "fill_price": float(fill_price) if fill_price else None,
            "symbol": spec.symbol,
            "side": order_request.side,
            "quantity": order_request.quantity,
        }

    def cancel_order(self, order_id: int | str) -> None:
        self._require_connection()
        order_id = int(order_id)
        trade = self._trades_by_order_id.get(order_id)
        if trade is None:
            raise ValueError(f"order_id {order_id} not found")
        self.ib.cancelOrder(trade.order)
        logger.warning("Cancelled order {}", order_id)

    def get_order_status(self, order_id: int | str) -> str:
        order_id = int(order_id)
        trade = self._trades_by_order_id.get(order_id)
        if trade is None:
            return "UNKNOWN"
        if trade.orderStatus is None:
            return "SUBMITTED"
        return str(trade.orderStatus.status)

    def _require_connection(self) -> None:
        if not self.is_connected():
            raise RuntimeError("IBKR client is not connected")
