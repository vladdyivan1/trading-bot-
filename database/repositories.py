"""Repository layer for database operations."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.dialects.sqlite import insert

from database.db import SessionLocal
from database.models import BacktestRun, HistoricalBar, LLMRecommendation, SignalLog, TradeLog


class HistoricalDataRepository:
    """Persistence helpers for OHLCV data."""

    def save_bars(
        self,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
        bars: pd.DataFrame,
    ) -> int:
        if bars.empty:
            return 0

        records: list[dict] = []
        for idx, row in bars.iterrows():
            ts = pd.Timestamp(idx).to_pydatetime()
            records.append(
                {
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "exchange": exchange,
                    "currency": currency,
                    "timeframe": timeframe,
                    "timestamp": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0.0)),
                }
            )

        with SessionLocal() as session:
            stmt = insert(HistoricalBar).values(records)
            upsert = stmt.on_conflict_do_update(
                index_elements=[
                    "symbol",
                    "asset_class",
                    "exchange",
                    "currency",
                    "timeframe",
                    "timestamp",
                ],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            session.execute(upsert)
            session.commit()
        return len(records)

    def load_bars(
        self,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        with SessionLocal() as session:
            stmt = select(HistoricalBar).where(
                and_(
                    HistoricalBar.symbol == symbol,
                    HistoricalBar.asset_class == asset_class,
                    HistoricalBar.exchange == exchange,
                    HistoricalBar.currency == currency,
                    HistoricalBar.timeframe == timeframe,
                )
            )
            if start is not None:
                stmt = stmt.where(HistoricalBar.timestamp >= start)
            if end is not None:
                stmt = stmt.where(HistoricalBar.timestamp <= end)

            rows = session.execute(stmt.order_by(HistoricalBar.timestamp.asc())).scalars().all()

        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(
            [
                {
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                }
                for row in rows
            ]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.set_index("timestamp").sort_index()


class TradeRepository:
    def log_trade(self, trade_payload: dict) -> int:
        with SessionLocal() as session:
            trade = TradeLog(**trade_payload)
            session.add(trade)
            session.commit()
            session.refresh(trade)
            return int(trade.id)

    def list_recent(self, limit: int = 200) -> list[TradeLog]:
        with SessionLocal() as session:
            stmt = select(TradeLog).order_by(TradeLog.created_at.desc()).limit(limit)
            return list(session.execute(stmt).scalars().all())


class SignalRepository:
    def log_signal(self, symbol: str, strategy_name: str, signal: dict, accepted: bool, rejection_reason: str = "") -> int:
        with SessionLocal() as session:
            row = SignalLog(
                symbol=symbol,
                strategy_name=strategy_name,
                signal_json=json.dumps(signal),
                accepted=accepted,
                rejection_reason=rejection_reason,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)


class BacktestRepository:
    def save_run(self, payload: dict) -> int:
        with SessionLocal() as session:
            row = BacktestRun(**payload)
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)


class LLMRecommendationRepository:
    def log(self, context_type: str, payload: dict, response: dict) -> int:
        with SessionLocal() as session:
            row = LLMRecommendation(
                context_type=context_type,
                payload_json=json.dumps(payload, default=str),
                response_json=json.dumps(response, default=str),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)
