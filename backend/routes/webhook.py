"""TradingView webhook endpoint."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.alerts import WebhookResponse
from backend.services.webhook_processor import WebhookProcessor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


@router.post("/webhook/tradingview", response_model=WebhookResponse)
async def tradingview_webhook(request: Request, db: Session = Depends(get_db)) -> WebhookResponse:
    """Receive TradingView alert JSON. Designed for low-latency processing."""
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raw = await request.body()
        logger.warning("Non-JSON webhook body: %s", raw[:200])
        return WebhookResponse(status="error", alert_id="unknown", rejection_reason="INVALID_JSON")

    processor = WebhookProcessor(db)
    return processor.process(body)
