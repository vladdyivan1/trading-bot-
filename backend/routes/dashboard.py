"""Built-in operational dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.services.analytics_service import AnalyticsService
from dashboard.templates import render_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)) -> str:
    metrics = AnalyticsService(get_settings()).metrics(db)
    return render_dashboard(metrics)


@router.get("/api/dashboard")
def dashboard_json(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(get_settings()).metrics(db)
