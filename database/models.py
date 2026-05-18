"""SQLAlchemy ORM models for persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base


class HistoricalBar(Base):
    __tablename__ = "historical_bars"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "asset_class",
            "exchange",
            "currency",
            "timeframe",
            "timestamp",
            name="uq_hist_bar",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="SMART")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    timeframe: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(16), default="STK")
    timeframe: Mapped[str] = mapped_column(String(16), default="5 mins")
    strategy_name: Mapped[str] = mapped_column(String(64), default="unknown")
    direction: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    llm_setup_quality: Mapped[float | None] = mapped_column(Float, nullable=True)


class SignalLog(Base):
    __tablename__ = "signal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    strategy_name: Mapped[str] = mapped_column(String(64))
    signal_json: Mapped[str] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(16), default="STK")
    timeframe: Mapped[str] = mapped_column(String(16), default="5 mins")
    start_ts: Mapped[datetime] = mapped_column(DateTime)
    end_ts: Mapped[datetime] = mapped_column(DateTime)
    metrics_json: Mapped[str] = mapped_column(Text)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")


class LLMRecommendation(Base):
    __tablename__ = "llm_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    context_type: Mapped[str] = mapped_column(String(32), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    response_json: Mapped[str] = mapped_column(Text)


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    __table_args__ = (
        UniqueConstraint(
            "strategy_name",
            "symbol",
            "asset_class",
            "timeframe",
            "market_regime",
            name="uq_strategy_performance",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(16), default="STK")
    timeframe: Mapped[str] = mapped_column(String(16), default="5 mins")
    market_regime: Mapped[str] = mapped_column(String(32), default="unknown")
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
