"""TradingView webhook endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.schemas.decision import DecisionEnvelope
from backend.schemas.tradingview import TradingViewAlert
from backend.services.decision_service import DecisionService

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/tradingview", response_model=DecisionEnvelope)
async def tradingview_webhook(request: Request, db: Session = Depends(get_db)) -> DecisionEnvelope:
    settings = get_settings()
    payload = await request.json()
    if settings.webhook_secret and payload.get("secret") != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
    try:
        alert = TradingViewAlert.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    service = DecisionService(settings)
    return service.process(db, alert)
