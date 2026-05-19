import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entities import AlertRecord, DecisionRecord, NewsSnapshot, PositionRecord
from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import AIDecision
from backend.schemas.execution import ExecutionResult


def make_alert_id(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class AlertStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_alert(
        self, alert: TradingViewAlert, payload: dict, alert_id: str | None = None
    ) -> AlertRecord:
        aid = alert_id or make_alert_id(payload)
        existing = await self.session.execute(
            select(AlertRecord).where(AlertRecord.alert_id == aid)
        )
        existing_rec = existing.scalar_one_or_none()
        if existing_rec:
            return existing_rec

        record = AlertRecord(
            alert_id=aid,
            ticker=alert.ticker,
            payload=payload,
            normalized=alert.model_dump(),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def mark_processed(self, alert_id: str) -> None:
        result = await self.session.execute(
            select(AlertRecord).where(AlertRecord.alert_id == alert_id)
        )
        rec = result.scalar_one_or_none()
        if rec:
            rec.processed = True

    async def save_decision(self, alert_id: str, decision: AIDecision, rejections: list[str]) -> None:
        self.session.add(
            DecisionRecord(
                alert_id=alert_id,
                decision=decision.decision.value,
                direction=decision.direction.value,
                confidence=decision.confidence,
                reason_summary=decision.reason_summary,
                news_sentiment=decision.news_sentiment.value,
                market_regime=decision.market_regime.value,
                risk_flags=decision.risk_flags,
                size_modifier=decision.size_modifier,
                rejection_reasons=rejections,
                full_response=decision.model_dump(mode="json"),
            )
        )

    async def save_news(self, alert_id: str, headlines: list, sentiment: str, event_risk: bool) -> None:
        self.session.add(
            NewsSnapshot(
                alert_id=alert_id,
                headlines=headlines,
                sentiment=sentiment,
                event_risk=event_risk,
            )
        )

    async def save_position(self, alert_id: str, result: ExecutionResult, bucket: str | None) -> None:
        if not result.contract:
            return
        self.session.add(
            PositionRecord(
                order_id=result.order_id,
                alert_id=alert_id,
                symbol=result.contract.symbol,
                underlying=result.contract.underlying,
                option_type=result.contract.option_type,
                strike=result.contract.strike,
                expiration=result.contract.expiration,
                quantity=result.quantity,
                entry_price=result.entry_price,
                exit_price=result.exit_price,
                pnl=result.pnl,
                status=result.status,
                opened_at=result.opened_at or datetime.utcnow(),
                closed_at=result.closed_at,
                time_of_day_bucket=bucket,
            )
        )

    async def list_alerts(self, limit: int = 50) -> list[AlertRecord]:
        result = await self.session.execute(
            select(AlertRecord).order_by(AlertRecord.received_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_decisions(self, limit: int = 50) -> list[DecisionRecord]:
        result = await self.session.execute(
            select(DecisionRecord).order_by(DecisionRecord.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_positions(self, status: str | None = None, limit: int = 100) -> list[PositionRecord]:
        q = select(PositionRecord).order_by(PositionRecord.opened_at.desc()).limit(limit)
        if status:
            q = q.where(PositionRecord.status == status)
        result = await self.session.execute(q)
        return list(result.scalars().all())
