"""Repository helpers for persistent logs."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from database.models import BacktestLog, LLMRecommendationLog, SignalLog, TradeLog
from strategies.base_strategy import TradeSignal


class TradingRepository:
    """Thin repository around SQLAlchemy models."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def log_signal(self, signal: TradeSignal, strategy_name: str) -> SignalLog:
        row = SignalLog(
            symbol=signal.symbol,
            asset_class=signal.asset_class,
            timeframe=signal.timeframe,
            strategy=strategy_name,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence_score=signal.confidence_score,
            reason=signal.reason,
        )
        self.session.add(row)
        return row

    def log_trade(self, **kwargs: Any) -> TradeLog:
        row = TradeLog(**kwargs)
        self.session.add(row)
        return row

    def log_backtest(self, symbol: str, strategy: str, timeframe: str, metrics: dict[str, Any]) -> BacktestLog:
        row = BacktestLog(symbol=symbol, strategy=strategy, timeframe=timeframe, metrics_json=json.dumps(metrics))
        self.session.add(row)
        return row

    def log_llm_recommendation(
        self,
        symbol: str,
        strategy: str,
        trade_allowed: bool,
        setup_quality: float,
        market_regime: str,
        reasoning: str,
        risks: list[str],
        suggested_adjustments: dict[str, Any],
    ) -> LLMRecommendationLog:
        row = LLMRecommendationLog(
            symbol=symbol,
            strategy=strategy,
            trade_allowed=trade_allowed,
            setup_quality=setup_quality,
            market_regime=market_regime,
            reasoning=reasoning,
            risks_json=json.dumps(risks),
            suggested_adjustments_json=json.dumps(suggested_adjustments),
        )
        self.session.add(row)
        return row
