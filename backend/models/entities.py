from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (Index("ix_alert_events_symbol_received_at", "symbol", "received_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payload_id: Mapped[str | None] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(32))
    bias: Mapped[str] = mapped_column(String(32), default="neutral")
    setup: Mapped[str] = mapped_column(String(64), default="SPY_0DTE_SCALP")
    alert_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_event_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("alert_events.id"))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    decision_payload: Mapped[dict] = mapped_column(JSON)

    executions: Mapped[list["ExecutionRecord"]] = relationship(back_populates="alert_event")
    news_snapshots: Mapped[list["NewsSnapshot"]] = relationship(back_populates="alert_event")


class NewsSnapshot(Base):
    __tablename__ = "news_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_event_id: Mapped[int] = mapped_column(ForeignKey("alert_events.id"), index=True)
    sentiment: Mapped[str] = mapped_column(String(16))
    regime_hint: Mapped[str] = mapped_column(String(24))
    reason_summary: Mapped[str] = mapped_column(Text)
    headlines: Mapped[list[dict]] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    alert_event: Mapped["AlertEvent"] = relationship(back_populates="news_snapshots")


class ExecutionRecord(Base):
    __tablename__ = "execution_records"
    __table_args__ = (Index("ix_execution_records_status_opened", "status", "opened_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_event_id: Mapped[int] = mapped_column(ForeignKey("alert_events.id"), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="paper")
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    contract_symbol: Mapped[str] = mapped_column(String(64))
    expiration: Mapped[str] = mapped_column(String(16))
    strike: Mapped[float] = mapped_column(Float)
    delta: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    spread_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_hold_minutes: Mapped[int] = mapped_column(Integer, default=12)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_price: Mapped[float | None] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    execution_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    alert_event: Mapped["AlertEvent"] = relationship(back_populates="executions")


class RiskDailyState(Base):
    __tablename__ = "risk_daily_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    total_exposure: Mapped[float] = mapped_column(Float, default=0.0)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kill_switch_engaged: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
