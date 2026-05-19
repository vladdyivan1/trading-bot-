"""Replay historical webhook signals through AI/risk filters."""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.services.webhook_processor import WebhookProcessor

logger = logging.getLogger(__name__)


def replay_alerts(
    db: Session,
    payloads: list[dict[str, Any]],
    enable_ai: bool = True,
    enable_risk: bool = True,
) -> list[dict[str, Any]]:
    results = []
    processor = WebhookProcessor(db)
    if not enable_ai:
        processor.settings.enable_ai_filter = False
    if not enable_risk:
        processor.risk = type(processor.risk)(processor.settings)  # fresh state each run

    for i, payload in enumerate(payloads):
        payload = dict(payload)
        payload["_replay_index"] = i
        try:
            resp = processor.process(payload)
            results.append(
                {
                    "index": i,
                    "alert_id": resp.alert_id,
                    "status": resp.status,
                    "decision": resp.decision.model_dump() if resp.decision else None,
                    "rejection": resp.rejection_reason,
                }
            )
        except Exception as e:
            logger.exception("Replay failed at %s", i)
            results.append({"index": i, "error": str(e)})
    return results


def load_replay_file(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else [data]
