"""SPY 0DTE Scalper — FastAPI webhook backend."""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings
from backend.database import init_db
from backend.routes import dashboard_router, health_router, webhook_router

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    await init_db()
    yield


app = FastAPI(
    title="SPY 0DTE Scalper",
    description="TradingView webhooks → AI/news filter → risk → paper execution",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)

dashboard_path = ROOT / "dashboard" / "static"
if dashboard_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")

# Jinja dashboard at /
from backend.routes.dashboard_pages import router as pages_router  # noqa: E402

app.include_router(pages_router)
