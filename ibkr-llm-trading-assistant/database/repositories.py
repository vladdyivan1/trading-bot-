"""Data access repositories."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.models import (
    BacktestRun,
    CandleBar,
    LLMRecommendation,
    SignalLog,
    StrategyPerformance,
    TradeLog,
)


class CandleRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_bars(
        self,
        df: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> int:
        count = 0
        for _, row in df.iterrows():
            bar_time = pd.Timestamp(row.name if "datetime" not in row else row.get("datetime", row.name))
            if hasattr(bar_time, "to_pydatetime"):
                bar_time = bar_time.to_pydatetime()
            existing = self.session.execute(
                select(CandleBar).where(
                    CandleBar.symbol == symbol,
                    CandleBar.asset_class == asset_class,
                    CandleBar.timeframe == timeframe,
                    CandleBar.bar_time == bar_time,
                )
            ).scalar_one_or_none()
            if existing:
                continue
            self.session.add(
                CandleBar(
                    symbol=symbol,
                    asset_class=asset_class,
                    exchange=exchange,
                    currency=currency,
                    timeframe=timeframe,
                    bar_time=bar_time,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
                )
            )
            count += 1
        return count

    def load_bars(
        self,
        symbol: str,
        asset_class: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        q = select(CandleBar).where(
            CandleBar.symbol == symbol,
            CandleBar.asset_class == asset_class,
            CandleBar.timeframe == timeframe,
        )
        if start:
            q = q.where(CandleBar.bar_time >= start)
        if end:
            q = q.where(CandleBar.bar_time <= end)
        q = q.order_by(CandleBar.bar_time)
        rows = self.session.execute(q).scalars().all()
        if not rows:
            return pd.DataFrame()
        data = [
            {
                "datetime": r.bar_time,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
        df = pd.DataFrame(data)
        df.set_index("datetime", inplace=True)
        return df


class TradeRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_trade(self, **kwargs) -> TradeLog:
        trade = TradeLog(**kwargs)
        self.session.add(trade)
        self.session.flush()
        return trade

    def get_open_trades(self, is_paper: bool = True) -> list[TradeLog]:
        q = select(TradeLog).where(
            TradeLog.status.in_(["submitted", "filled", "open"]),
            TradeLog.is_paper == is_paper,
        )
        return list(self.session.execute(q).scalars().all())

    def get_trades_today(self, is_paper: bool = True) -> list[TradeLog]:
        today = datetime.utcnow().date()
        trades = self.get_recent_trades(limit=500, is_paper=is_paper)
        return [t for t in trades if t.created_at.date() == today]

    def get_recent_trades(self, limit: int = 100, is_paper: bool = True) -> list[TradeLog]:
        q = (
            select(TradeLog)
            .where(TradeLog.is_paper == is_paper)
            .order_by(TradeLog.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(q).scalars().all())


class SignalRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_signal(self, signal_json: str, symbol: str, strategy_name: str, **kwargs) -> SignalLog:
        log = SignalLog(
            symbol=symbol,
            strategy_name=strategy_name,
            signal_json=signal_json,
            **kwargs,
        )
        self.session.add(log)
        return log


class BacktestRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_run(self, strategy_name: str, symbol: str, timeframe: str, metrics: dict) -> BacktestRun:
        run = BacktestRun(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            metrics_json=json.dumps(metrics, default=str),
        )
        self.session.add(run)
        return run


class LLMRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_recommendation(
        self, context_type: str, input_summary: str, response: dict
    ) -> LLMRecommendation:
        rec = LLMRecommendation(
            context_type=context_type,
            input_summary=input_summary,
            response_json=json.dumps(response),
            trade_allowed=response.get("trade_allowed", False),
        )
        self.session.add(rec)
        return rec


class StrategyPerformanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_performance(
        self,
        strategy_name: str,
        symbol: str,
        asset_class: str,
        timeframe: str,
        **metrics,
    ) -> StrategyPerformance:
        existing = self.session.execute(
            select(StrategyPerformance).where(
                StrategyPerformance.strategy_name == strategy_name,
                StrategyPerformance.symbol == symbol,
                StrategyPerformance.timeframe == timeframe,
            )
        ).scalar_one_or_none()
        if existing:
            for k, v in metrics.items():
                setattr(existing, k, v)
            return existing
        perf = StrategyPerformance(
            strategy_name=strategy_name,
            symbol=symbol,
            asset_class=asset_class,
            timeframe=timeframe,
            **metrics,
        )
        self.session.add(perf)
        return perf

    def get_ranked_strategies(self, limit: int = 20) -> list[StrategyPerformance]:
        q = (
            select(StrategyPerformance)
            .order_by(StrategyPerformance.rank_score.desc())
            .limit(limit)
        )
        return list(self.session.execute(q).scalars().all())
