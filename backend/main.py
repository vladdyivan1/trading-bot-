from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.models import Base, engine
from backend.routes import dashboard_router, replay_router, webhook_router
from backend.schemas.api import HealthResponse
from backend.services.logging import configure_logging
from backend.services.settings import settings

configure_logging()
settings.data_dir.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TradingView AI 0DTE Scalper",
    version="1.0.0",
    description="Webhook backend that filters and scores trade opportunities in real time.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(replay_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    mode = "paper" if settings.paper_trading_mode else f"broker:{getattr(settings, 'broker_adapter', 'paper')}"
    return HealthResponse(status="ok", mode=mode)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


dashboard_dir = Path(__file__).resolve().parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
