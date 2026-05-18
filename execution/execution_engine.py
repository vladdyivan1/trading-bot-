"""Execution engine that applies risk checks before paper trading."""

from __future__ import annotations

from dataclasses import dataclass

from database.db import get_session, init_db
from database.repositories import TradingRepository
from execution.paper_trader import PaperFill, PaperTrader
from risk.risk_manager import RiskContext, RiskDecision, RiskManager
from strategies.base_strategy import TradeSignal


@dataclass
class ExecutionResult:
    accepted: bool
    risk_decision: RiskDecision
    fill: PaperFill | None = None


class ExecutionEngine:
    """Validate signals, log decisions, and execute paper trades."""

    def __init__(self, risk_manager: RiskManager | None = None, paper_trader: PaperTrader | None = None) -> None:
        self.risk_manager = risk_manager or RiskManager()
        self.paper_trader = paper_trader or PaperTrader()
        init_db()

    def execute_paper_signal(self, signal: TradeSignal, context: RiskContext, strategy_name: str = "unknown") -> ExecutionResult:
        decision = self.risk_manager.validate_signal(signal, context)
        with get_session() as session:
            repo = TradingRepository(session)
            repo.log_signal(signal, strategy_name)
        if not decision.allowed:
            return ExecutionResult(accepted=False, risk_decision=decision)

        side = "BUY" if signal.direction == "long" else "SELL"
        fill = self.paper_trader.place_market_order(
            symbol=signal.symbol,
            asset_class=signal.asset_class,
            side=side,
            quantity=decision.quantity,
            reference_price=signal.entry_price,
        )
        with get_session() as session:
            repo = TradingRepository(session)
            repo.log_trade(
                symbol=signal.symbol,
                asset_class=signal.asset_class,
                strategy=strategy_name,
                direction=signal.direction,
                quantity=decision.quantity,
                entry_price=fill.fill_price,
                status=fill.status,
                broker_order_id=fill.order_id,
            )
        return ExecutionResult(accepted=True, risk_decision=decision, fill=fill)

    def monitor_open_trades(self) -> list[dict[str, object]]:
        return self.paper_trader.open_trades()
