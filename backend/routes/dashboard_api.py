"""Dashboard REST API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.schemas.dashboard import DashboardStats
from backend.services.dashboard_service import get_dashboard_stats
from execution.paper_executor import get_executor

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)) -> DashboardStats:
    return get_dashboard_stats(db)


@router.get("/config")
def config():
    s = get_settings()
    return {
        "execution_mode": s.execution_mode.value,
        "enable_ai_filter": s.enable_ai_filter,
        "enable_news_filter": s.enable_news_filter,
        "enable_broker_execution": s.enable_broker_execution,
        "risk_preset": s.risk_preset.value,
        "kill_switch": s.kill_switch,
    }


@router.get("/positions/open")
def open_positions():
    return get_executor().get_open_positions()
