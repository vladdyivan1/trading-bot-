"""Aggregate dashboard analytics."""

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.entities import AIDecisionRecord, AlertRecord, Position, TradeExecution
from backend.schemas.dashboard import DashboardStats


def get_dashboard_stats(db: Session, limit: int = 50) -> DashboardStats:
    total_alerts = db.query(func.count(AlertRecord.id)).scalar() or 0
    decisions = db.query(AIDecisionRecord).order_by(AIDecisionRecord.created_at.desc()).limit(500).all()

    approved = sum(1 for d in decisions if d.decision == "APPROVE")
    rejected = sum(1 for d in decisions if d.decision == "REJECT")
    wait = sum(1 for d in decisions if d.decision == "WAIT")
    reduce = sum(1 for d in decisions if d.decision == "REDUCE_SIZE")

    rejection_reasons: Counter = Counter()
    for d in decisions:
        if d.decision in ("REJECT", "WAIT"):
            rejection_reasons[d.reason_summary[:80]] += 1

    sentiment_bd: Counter = Counter(d.news_sentiment for d in decisions)
    regime_bd: Counter = Counter(d.market_regime for d in decisions)

    positions = db.query(Position).all()
    open_pos = [p for p in positions if p.status == "OPEN"]
    closed = [p for p in positions if p.status == "CLOSED"]
    total_pnl = sum(p.pnl for p in closed)
    wins = sum(1 for p in closed if p.pnl > 0)
    win_rate = wins / len(closed) if closed else 0.0

    # Time-of-day buckets from executions
    tod: dict[str, list[float]] = {}
    execs = db.query(TradeExecution).order_by(TradeExecution.executed_at.desc()).limit(200).all()
    for ex in execs:
        hour = ex.executed_at.hour if ex.executed_at else 0
        bucket = f"{hour:02d}:00"
        tod.setdefault(bucket, [])

    recent_alerts = [
        {"alert_id": a.alert_id, "received_at": a.received_at.isoformat(), "processed": a.processed}
        for a in db.query(AlertRecord).order_by(AlertRecord.received_at.desc()).limit(limit).all()
    ]
    recent_decisions = [
        {
            "alert_id": d.alert_id,
            "decision": d.decision,
            "direction": d.direction,
            "confidence": d.confidence,
            "reason": d.reason_summary,
            "sentiment": d.news_sentiment,
            "regime": d.market_regime,
            "at": d.created_at.isoformat(),
        }
        for d in decisions[:limit]
    ]

    return DashboardStats(
        total_alerts=total_alerts,
        approved=approved,
        rejected=rejected,
        wait=wait,
        reduce_size=reduce,
        open_positions=len(open_pos),
        closed_positions=len(closed),
        total_pnl=total_pnl,
        win_rate=round(win_rate, 3),
        max_drawdown=0.0,
        rejection_reasons=dict(rejection_reasons.most_common(20)),
        sentiment_breakdown=dict(sentiment_bd),
        regime_breakdown=dict(regime_bd),
        time_of_day_performance={k: {"count": len(v)} for k, v in tod.items()},
        recent_alerts=recent_alerts,
        recent_decisions=recent_decisions,
    )
