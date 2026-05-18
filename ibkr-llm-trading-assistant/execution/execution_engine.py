"""Orchestrates signal validation, risk checks, and paper execution."""

from __future__ import annotations

from loguru import logger

from ai.signal_analyzer import SignalAnalyzer
from ai.trade_reviewer import TradeReviewer
from database.db import get_session
from database.repositories import BacktestRepository, SignalRepository, StrategyPerformanceRepository
from execution.paper_trader import PaperTrader
from risk.risk_manager import RiskManager
from schemas import LLMRecommendation, TradeSignal


class ExecutionEngine:
    """
    End-to-end pipeline: signal → LLM review → risk → paper trade.

    The LLM never places orders; only this engine calls PaperTrader after risk approval.
    """

    def __init__(
        self,
        risk_manager: RiskManager | None = None,
        paper_trader: PaperTrader | None = None,
        signal_analyzer: SignalAnalyzer | None = None,
        trade_reviewer: TradeReviewer | None = None,
    ) -> None:
        self.risk = risk_manager or RiskManager()
        self.trader = paper_trader or PaperTrader()
        self.analyzer = signal_analyzer or SignalAnalyzer()
        self.reviewer = trade_reviewer or TradeReviewer()

    def process_signal(
        self,
        signal: TradeSignal,
        market_summary: dict | None = None,
        backtest_metrics: dict | None = None,
        backtest_trades: int = 0,
        spread_pct: float = 0.0,
        skip_llm: bool = False,
    ) -> dict:
        """Full pipeline for a single trade signal."""
        llm_rec: LLMRecommendation | None = None
        if not skip_llm:
            llm_rec = self.analyzer.analyze(signal, market_summary, backtest_metrics)

        risk_result = self.risk.validate(
            signal,
            llm=llm_rec,
            backtest_trades=backtest_trades,
            spread_pct=spread_pct,
        )

        with get_session() as session:
            SignalRepository(session).log_signal(
                signal.model_dump_json_safe(),
                risk_result.approved,
                signal.strategy_name,
            )

        if not risk_result.approved:
            return {
                "executed": False,
                "reasons": risk_result.reasons,
                "llm": llm_rec.model_dump() if llm_rec else None,
            }

        qty = risk_result.adjusted_quantity or 0
        try:
            result = self.trader.execute(signal, qty)
            self.risk.state.open_positions += 1
            return {
                "executed": True,
                "order": result,
                "quantity": qty,
                "llm": llm_rec.model_dump() if llm_rec else None,
            }
        except Exception as exc:
            logger.error("Execution failed: {}", exc)
            return {"executed": False, "reasons": [str(exc)], "llm": llm_rec.model_dump() if llm_rec else None}

    def update_performance(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        asset_class: str,
        win_rate: float,
        expectancy: float,
        total_trades: int,
    ) -> None:
        with get_session() as session:
            StrategyPerformanceRepository(session).update_ranking(
                strategy_name, symbol, timeframe, asset_class, win_rate, expectancy, total_trades
            )
