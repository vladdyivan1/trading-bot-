"""Data access repositories."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from database.models import (
    BacktestRun,
    LLMLog,
    OHLCVBar,
    SignalLog,
    StrategyPerformance,
    TradeLog,
)


class OHLCVRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_bars(self, df: pd.DataFrame) -> int:
        """Insert or ignore duplicate OHLCV bars."""
        if df.empty:
            return 0
        records = df.to_dict(orient="records")
        stmt = sqlite_insert(OHLCVBar).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "asset_class", "timeframe", "bar_time"])
        result = self.session.execute(stmt)
        return result.rowcount or len(records)

    def load_bars(
        self,
        symbol: str,
        timeframe: str,
        asset_class: str = "STK",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        q = select(OHLCVBar).where(
            OHLCVBar.symbol == symbol,
            OHLCVBar.timeframe == timeframe,
            OHLCVBar.asset_class == asset_class,
        )
        if start:
            q = q.where(OHLCVBar.bar_time >= start)
        if end:
            q = q.where(OHLCVBar.bar_time <= end)
        q = q.order_by(OHLCVBar.bar_time)
        rows = self.session.scalars(q).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "bar_time": r.bar_time,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "symbol": r.symbol,
                    "asset_class": r.asset_class,
                    "timeframe": r.timeframe,
                }
                for r in rows
            ]
        ).set_index("bar_time")


class TradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_trade(self, **kwargs) -> TradeLog:
        trade = TradeLog(**kwargs)
        self.session.add(trade)
        self.session.flush()
        return trade

    def get_open_trades(self) -> list[TradeLog]:
        q = select(TradeLog).where(TradeLog.status.in_(["pending", "open", "submitted"]))
        return list(self.session.scalars(q).all())

    def update_trade(self, trade_id: int, **kwargs) -> None:
        trade = self.session.get(TradeLog, trade_id)
        if trade:
            for k, v in kwargs.items():
                setattr(trade, k, v)


class SignalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_signal(self, payload: dict, approved: bool, strategy_name: str) -> None:
        self.session.add(
            SignalLog(
                symbol=payload.get("symbol", ""),
                strategy_name=strategy_name,
                direction=payload.get("direction", ""),
                confidence_score=float(payload.get("confidence_score", 0)),
                payload_json=json.dumps(payload),
                approved=approved,
            )
        )


class BacktestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_run(
        self, strategy_name: str, symbol: str, timeframe: str, metrics: dict
    ) -> None:
        self.session.add(
            BacktestRun(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                metrics_json=json.dumps(metrics),
            )
        )


class StrategyPerformanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def update_ranking(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        asset_class: str,
        win_rate: float,
        expectancy: float,
        total_trades: int,
    ) -> None:
        score = expectancy * 0.6 + win_rate * 0.4
        existing = self.session.scalars(
            select(StrategyPerformance).where(
                StrategyPerformance.strategy_name == strategy_name,
                StrategyPerformance.symbol == symbol,
                StrategyPerformance.timeframe == timeframe,
            )
        ).first()
        if existing:
            existing.win_rate = win_rate
            existing.expectancy = expectancy
            existing.total_trades = total_trades
            existing.ranking_score = score
            existing.updated_at = datetime.utcnow()
        else:
            self.session.add(
                StrategyPerformance(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    asset_class=asset_class,
                    win_rate=win_rate,
                    expectancy=expectancy,
                    total_trades=total_trades,
                    ranking_score=score,
                )
            )

    def get_rankings(self, limit: int = 20) -> list[StrategyPerformance]:
        q = (
            select(StrategyPerformance)
            .order_by(StrategyPerformance.ranking_score.desc())
            .limit(limit)
        )
        return list(self.session.scalars(q).all())


class LLMRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_response(self, symbol: str, response: dict) -> None:
        self.session.add(
            LLMLog(
                symbol=symbol,
                trade_allowed=bool(response.get("trade_allowed", False)),
                setup_quality=float(response.get("setup_quality", 0)),
                response_json=json.dumps(response),
            )
        )
