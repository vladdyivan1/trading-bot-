"""Dashboard analytics for alerts, decisions, positions, and replay outcomes."""

from __future__ import annotations

from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.models import Alert, Decision, Order, Position


class AnalyticsService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tz = ZoneInfo(settings.market_timezone)

    def metrics(self, db: Session) -> dict:
        alerts = db.scalars(select(Alert).order_by(Alert.received_at.desc()).limit(500)).all()
        decisions = db.scalars(select(Decision).order_by(Decision.created_at.desc()).limit(500)).all()
        positions = db.scalars(select(Position).order_by(Position.opened_at.desc()).limit(500)).all()
        orders = db.scalars(select(Order).order_by(Order.created_at.asc()).limit(1000)).all()

        rejection_counter: Counter[str] = Counter()
        sentiment_counter: Counter[str] = Counter()
        regime_counter: Counter[str] = Counter()
        for decision in decisions:
            sentiment_counter[decision.news_sentiment] += 1
            regime_counter[decision.market_regime] += 1
            for reason in decision.rejection_reasons or []:
                rejection_counter[reason] += 1

        time_of_day: dict[str, dict[str, float | int]] = defaultdict(lambda: {"trades": 0, "pnl": 0.0})
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        winning = 0
        closed_count = 0
        for order in orders:
            bucket = order.created_at.astimezone(self.tz).strftime("%H:00")
            time_of_day[bucket]["trades"] += 1
            time_of_day[bucket]["pnl"] += order.realized_pnl
            equity += order.realized_pnl
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, equity - peak)
            if order.realized_pnl != 0:
                closed_count += 1
                if order.realized_pnl > 0:
                    winning += 1

        open_positions = [position for position in positions if position.status == "OPEN"]
        closed_positions = [position for position in positions if position.status == "CLOSED"]
        return {
            "alerts": len(alerts),
            "approved": sum(1 for decision in decisions if decision.approved),
            "rejected": sum(1 for decision in decisions if decision.decision == "REJECT"),
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "pnl": sum(order.realized_pnl for order in orders),
            "win_rate": winning / closed_count if closed_count else 0.0,
            "max_drawdown": abs(max_drawdown),
            "rejection_reasons": dict(rejection_counter),
            "time_of_day": dict(sorted(time_of_day.items())),
            "sentiment_heatmap": dict(sentiment_counter),
            "regime_counts": dict(regime_counter),
        }
