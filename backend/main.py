"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import init_db
from backend.routes import dashboard_api, health, webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    init_db()
    logger.info("Database initialized — mode=%s", get_settings().execution_mode.value)
    yield


app = FastAPI(
    title="SPY 0DTE Scalping System",
    description="TradingView webhooks → AI/news filter → risk → paper execution",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(dashboard_api.router)

dashboard_path = Path(__file__).resolve().parent.parent / "dashboard" / "static"
if dashboard_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")


@app.get("/")
def root():
    return {
        "service": "SPY 0DTE Scalping System",
        "webhook": "/webhook/tradingview",
        "dashboard": "/dashboard/",
        "health": "/health",
    }
