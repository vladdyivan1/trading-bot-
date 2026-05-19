from fastapi import APIRouter

from backend.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    s = get_settings()
    return {
        "status": "ok",
        "execution_mode": s.execution_mode,
        "enable_ai_filter": s.enable_ai_filter,
        "enable_news_filter": s.enable_news_filter,
        "enable_broker_execution": s.enable_broker_execution,
        "kill_switch": s.kill_switch,
    }
