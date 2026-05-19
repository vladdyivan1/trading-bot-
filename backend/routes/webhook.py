from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.schemas.api import WebhookResponse
from backend.schemas.tradingview import TradingViewAlert
from backend.services.container import get_pipeline
from backend.services.settings import settings

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/tradingview", response_model=WebhookResponse)
def tradingview_webhook(
    payload: TradingViewAlert,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
) -> WebhookResponse:
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook secret validation failed.",
        )

    pipeline = get_pipeline()
    event, decision, idempotent = pipeline.process_alert(db, payload)
    return WebhookResponse(
        event_id=event.id,
        idempotent_replay=idempotent,
        processed_at=datetime.now(UTC),
        decision=decision,
    )
