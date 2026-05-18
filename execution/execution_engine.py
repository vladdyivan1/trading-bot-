"""Execution engine coordinating signal logging, risk checks, and paper orders."""

from __future__ import annotations

import json
from dataclasses import dataclass

from database.repositories import SignalRepository, TradeRepository
from execution.paper_trader import PaperTrader
from risk.risk_manager import AccountSnapshot, RiskManager
from strategies.base_strategy import StrategySignal


@dataclass
class ExecutionResult:
    accepted: bool
    message: str
    order_info: dict | None = None


class ExecutionEngine:
    def __init__(self, risk_manager: RiskManager, paper_trader: PaperTrader) -> None:
        self.risk_manager = risk_manager
        self.paper_trader = paper_trader
        self.signal_repo = SignalRepository()
        self.trade_repo = TradeRepository()

    def process_signal(
        self,
        signal: StrategySignal,
        account_snapshot: AccountSnapshot,
        model_confidence: float,
        backtest_sample_size: int,
        spread_pct: float,
    ) -> ExecutionResult:
        decision = self.risk_manager.evaluate(
            signal=signal,
            account=account_snapshot,
            model_confidence=model_confidence,
            backtest_sample_size=backtest_sample_size,
            spread_pct=spread_pct,
        )

        self.signal_repo.log_signal(
            symbol=signal.symbol,
            strategy_name=signal.strategy_name,
            signal=signal.model_dump(mode="json"),
            accepted=decision.trade_allowed,
            rejection_reason="; ".join(decision.reasons),
        )

        if not decision.trade_allowed:
            return ExecutionResult(False, f"Trade blocked: {decision.reasons}")

        order_info = self.paper_trader.execute_signal(signal, quantity=decision.approved_quantity)

        trade_payload = {
            "symbol": signal.symbol,
            "asset_class": signal.asset_class,
            "timeframe": signal.timeframe,
            "strategy_name": signal.strategy_name,
            "direction": signal.direction,
            "quantity": int(decision.approved_quantity),
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "status": order_info.get("status", "Submitted"),
            "order_id": order_info.get("order_id"),
            "fill_price": order_info.get("fill_price"),
            "commission": 0.0,
            "reason": signal.reason,
            "metadata_json": json.dumps(order_info),
            "llm_setup_quality": None,
        }
        self.trade_repo.log_trade(trade_payload)

        return ExecutionResult(True, "Paper order submitted", order_info=order_info)
