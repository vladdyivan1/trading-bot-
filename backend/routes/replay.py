from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.services.replay_service import ReplayService

router = APIRouter(prefix="/replay", tags=["replay"])
service = ReplayService()


@router.post("/run")
def run_replay(limit: int = Query(default=500, ge=1, le=10_000), db: Session = Depends(get_db)) -> dict:
    return service.run(db, limit=limit)
