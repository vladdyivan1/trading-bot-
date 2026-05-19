import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.schemas.alerts import WebhookResponse
from backend.services.alert_store import AlertStore
from backend.services.webhook_processor import WebhookProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/tradingview", response_model=WebhookResponse)
async def tradingview_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_webhook_secret),
) -> WebhookResponse:
    """Receive TradingView alert JSON; filter and score via AI/news + risk; paper execute."""
    try:
        body: dict[str, Any] = await request.json()
    except Exception as e:
        logger.error("Invalid JSON payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    store = AlertStore(db)
    processor = WebhookProcessor(store)
    response = await processor.process(body)
    logger.info(
        "Webhook processed: decision=%s direction=%s confidence=%s",
        response.decision,
        response.direction,
        response.confidence,
    )
    return response
