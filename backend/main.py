"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from backend.config import get_settings
from backend.database import init_db
from backend.routes.dashboard import router as dashboard_router
from backend.routes.webhook import router as webhook_router


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="TradingView webhook backend for AI-assisted SPY 0DTE/options scalping.",
    )

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": settings.environment,
            "paper_trading": settings.paper_trading,
            "broker_execution": settings.enable_broker_execution,
            "ai_filter": settings.enable_ai_filter,
            "news_filter": settings.enable_news_filter,
        }

    app.include_router(webhook_router)
    app.include_router(dashboard_router)
    return app


app = create_app()
