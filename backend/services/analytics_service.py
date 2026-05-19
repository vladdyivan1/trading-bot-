from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.entities import AlertEvent, ExecutionRecord, NewsSnapshot

ET = ZoneInfo("America/New_York")


class AnalyticsService:
    def summary(self, db: Session) -> dict:
        alerts = db.execute(select(AlertEvent)).scalars().all()
        decisions = [a.decision_payload.get("decision", "UNKNOWN") for a in alerts]
        decision_counts = Counter(decisions)
        executions = db.execute(select(ExecutionRecord)).scalars().all()
        closed = [item for item in executions if item.status == "CLOSED"]
        wins = [item for item in closed if item.pnl > 0]
        realized_pnl = sum(item.pnl for item in closed)
        open_positions = [item for item in executions if item.status == "OPEN"]

        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for trade in sorted(closed, key=lambda row: row.closed_at or row.opened_at):
            equity += trade.pnl
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, equity - peak)

        return {
            "alerts_total": len(alerts),
            "approved": decision_counts.get("APPROVE", 0),
            "rejected": decision_counts.get("REJECT", 0),
            "wait": decision_counts.get("WAIT", 0),
            "reduce_size": decision_counts.get("REDUCE_SIZE", 0),
            "open_positions": len(open_positions),
            "closed_positions": len(closed),
            "realized_pnl": round(realized_pnl, 2),
            "win_rate": round((len(wins) / len(closed) * 100.0), 2) if closed else 0.0,
            "max_drawdown": round(max_drawdown, 2),
        }

    def recent_alerts(self, db: Session, limit: int = 50) -> list[dict]:
        rows = (
            db.execute(select(AlertEvent).order_by(desc(AlertEvent.received_at)).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "action": row.action,
                "bias": row.bias,
                "setup": row.setup,
                "received_at": row.received_at.isoformat(),
                "decision": row.decision_payload,
            }
            for row in rows
        ]

    def open_positions(self, db: Session) -> list[dict]:
        rows = db.execute(select(ExecutionRecord).where(ExecutionRecord.status == "OPEN")).scalars().all()
        return [self._position_payload(item) for item in rows]

    def closed_positions(self, db: Session, limit: int = 100) -> list[dict]:
        rows = (
            db.execute(
                select(ExecutionRecord)
                .where(ExecutionRecord.status == "CLOSED")
                .order_by(desc(ExecutionRecord.closed_at))
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [self._position_payload(item) for item in rows]

    def time_of_day_performance(self, db: Session) -> list[dict]:
        rows = db.execute(select(ExecutionRecord).where(ExecutionRecord.status == "CLOSED")).scalars().all()
        bucket: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            opened = row.opened_at.astimezone(ET) if row.opened_at.tzinfo else row.opened_at.replace(tzinfo=UTC).astimezone(ET)
            label = opened.strftime("%H:00")
            bucket[label].append(row.pnl)
        return [
            {
                "hour_et": hour,
                "trades": len(pnls),
                "avg_pnl": round(sum(pnls) / len(pnls), 3),
                "total_pnl": round(sum(pnls), 3),
            }
            for hour, pnls in sorted(bucket.items())
        ]

    def rejection_analytics(self, db: Session) -> list[dict]:
        rows = db.execute(select(AlertEvent)).scalars().all()
        reasons: Counter[str] = Counter()
        for row in rows:
            decision = row.decision_payload.get("decision")
            if decision != "REJECT":
                continue
            flags = row.decision_payload.get("risk_flags", [])
            if not flags:
                reasons["UNSPECIFIED"] += 1
            for flag in flags:
                reasons[flag] += 1
        return [{"reason": key, "count": count} for key, count in reasons.most_common()]

    def sentiment_heatmap(self, db: Session) -> list[dict]:
        rows = db.execute(select(NewsSnapshot)).scalars().all()
        matrix: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            ts = row.captured_at.astimezone(ET) if row.captured_at.tzinfo else row.captured_at.replace(tzinfo=UTC).astimezone(ET)
            hour = ts.strftime("%H:00")
            matrix[hour][row.sentiment] += 1
        payload: list[dict] = []
        for hour, counts in sorted(matrix.items()):
            payload.append({"hour_et": hour, **counts})
        return payload

    def regime_analytics(self, db: Session) -> list[dict]:
        rows = db.execute(select(AlertEvent)).scalars().all()
        counts: Counter[str] = Counter()
        for row in rows:
            counts[row.decision_payload.get("market_regime", "UNKNOWN")] += 1
        return [{"regime": regime, "count": count} for regime, count in counts.most_common()]

    def _position_payload(self, row: ExecutionRecord) -> dict:
        return {
            "id": row.id,
            "symbol": row.symbol,
            "contract_symbol": row.contract_symbol,
            "direction": row.direction,
            "quantity": row.quantity,
            "entry_price": row.entry_price,
            "exit_price": row.exit_price,
            "pnl": row.pnl,
            "status": row.status,
            "opened_at": row.opened_at.isoformat() if row.opened_at else None,
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        }
