from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.entities import DecisionRecord, NewsSnapshot, PositionRecord
from backend.services.alert_store import AlertStore
from backend.services.analytics import AnalyticsService

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/alerts")
async def recent_alerts(limit: int = 50, db: AsyncSession = Depends(get_db)):
    store = AlertStore(db)
    alerts = await store.list_alerts(limit)
    return [
        {
            "alert_id": a.alert_id,
            "ticker": a.ticker,
            "received_at": a.received_at.isoformat(),
            "normalized": a.normalized,
            "processed": a.processed,
        }
        for a in alerts
    ]


@router.get("/decisions")
async def recent_decisions(limit: int = 50, db: AsyncSession = Depends(get_db)):
    store = AlertStore(db)
    decisions = await store.list_decisions(limit)
    return [
        {
            "alert_id": d.alert_id,
            "created_at": d.created_at.isoformat(),
            "decision": d.decision,
            "direction": d.direction,
            "confidence": d.confidence,
            "reason_summary": d.reason_summary,
            "news_sentiment": d.news_sentiment,
            "market_regime": d.market_regime,
            "rejection_reasons": d.rejection_reasons,
        }
        for d in decisions
    ]


@router.get("/positions")
async def positions(status: str | None = None, db: AsyncSession = Depends(get_db)):
    store = AlertStore(db)
    pos = await store.list_positions(status, 100)
    return [
        {
            "order_id": p.order_id,
            "symbol": p.symbol,
            "option_type": p.option_type,
            "strike": p.strike,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "exit_price": p.exit_price,
            "pnl": p.pnl,
            "status": p.status,
            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
            "time_of_day_bucket": p.time_of_day_bucket,
        }
        for p in pos
    ]


@router.get("/analytics/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).summary()


@router.get("/analytics/rejections")
async def rejection_analytics(db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).rejection_breakdown()


@router.get("/analytics/time-of-day")
async def time_of_day_performance(db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).time_of_day_performance()


@router.get("/analytics/sentiment-heatmap")
async def sentiment_heatmap(db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).sentiment_heatmap()


@router.get("/analytics/regime")
async def regime_analytics(db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).regime_breakdown()
