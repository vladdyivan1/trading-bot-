"""Trade execution orchestrator — validates before placing orders."""

from __future__ import annotations

import json
from typing import Optional

from loguru import logger

from broker.ibkr_client import IBKRClient
from broker.orders import signal_to_order_side
from config.settings import get_settings
from database.db import get_db_session
from database.repositories import SignalRepository, TradeRepository
from risk.risk_manager import RiskManager
from schemas import BacktestResult, LLMTradeReview, RiskCheckResult, TradeSignal
from schemas import AssetClass


class ExecutionEngine:
    """
    Receives validated signals, checks risk, places paper trades.
    LLM recommendations are advisory only.
    """

    def __init__(
        self,
        client: Optional[IBKRClient] = None,
        risk_manager: Optional[RiskManager] = None,
    ):
        self.client = client or IBKRClient()
        self.risk = risk_manager or RiskManager()
        self.settings = get_settings()

    def process_signal(
        self,
        signal: TradeSignal,
        llm_review: Optional[LLMTradeReview] = None,
        backtest_result: Optional[BacktestResult] = None,
        model_confidence: Optional[float] = None,
    ) -> dict:
        """Full pipeline: log -> risk -> optional LLM gate -> execute."""
        with get_db_session() as session:
            SignalRepository(session).log_signal(
                signal.model_dump_json(),
                signal.symbol,
                signal.strategy_name,
            )

        if llm_review and not llm_review.trade_allowed:
            logger.info("LLM recommended against trade for {}", signal.symbol)
            return {"executed": False, "reason": "LLM trade_allowed=false"}

        account_value = self._get_account_value()
        open_positions = self.client.open_position_count() if self.client.is_connected else 0

        risk_result = self.risk.validate_signal(
            signal,
            account_value,
            open_positions,
            backtest_result,
            model_confidence,
        )

        if not risk_result.approved:
            return {"executed": False, "reason": risk_result.reasons}

        if self.settings.live_trading_enabled and not self.settings.ibkr_paper:
            return self._execute_live(signal, risk_result)
        return self._execute_paper(signal, risk_result)

    def _get_account_value(self) -> float:
        if self.client.is_connected:
            summary = self.client.account_summary()
            for key in ("NetLiquidation", "TotalCashValue"):
                if key in summary:
                    try:
                        return float(summary[key])
                    except (TypeError, ValueError):
                        pass
        return self.settings.initial_capital

    def _execute_paper(self, signal: TradeSignal, risk: RiskCheckResult) -> dict:
        from execution.paper_trader import PaperTrader

        trader = PaperTrader(self.client, self.risk)
        return trader.execute(signal, risk.adjusted_quantity or 1)

    def _execute_live(self, signal: TradeSignal, risk: RiskCheckResult) -> dict:
        if not self.settings.live_trading_enabled:
            return {"executed": False, "reason": "Live trading disabled"}
        from execution.live_trader import LiveTrader

        trader = LiveTrader(self.client, self.risk)
        return trader.execute(signal, risk.adjusted_quantity or 1)
