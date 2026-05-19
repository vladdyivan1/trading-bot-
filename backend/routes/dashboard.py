from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/dashboard-api", tags=["dashboard"])
service = AnalyticsService()


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    return service.summary(db)


@router.get("/alerts")
def recent_alerts(limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)) -> list[dict]:
    return service.recent_alerts(db, limit=limit)


@router.get("/positions/open")
def open_positions(db: Session = Depends(get_db)) -> list[dict]:
    return service.open_positions(db)


@router.get("/positions/closed")
def closed_positions(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[dict]:
    return service.closed_positions(db, limit=limit)


@router.get("/analytics/time-of-day")
def time_of_day(db: Session = Depends(get_db)) -> list[dict]:
    return service.time_of_day_performance(db)


@router.get("/analytics/rejections")
def rejections(db: Session = Depends(get_db)) -> list[dict]:
    return service.rejection_analytics(db)


@router.get("/analytics/sentiment-heatmap")
def sentiment_heatmap(db: Session = Depends(get_db)) -> list[dict]:
    return service.sentiment_heatmap(db)


@router.get("/analytics/regime")
def regime_analytics(db: Session = Depends(get_db)) -> list[dict]:
    return service.regime_analytics(db)
