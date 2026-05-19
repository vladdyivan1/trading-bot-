from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.schemas.decision import DecisionPayload


class WebhookResponse(BaseModel):
    event_id: int
    idempotent_replay: bool
    processed_at: datetime
    decision: DecisionPayload


class HealthResponse(BaseModel):
    status: str
    mode: str
