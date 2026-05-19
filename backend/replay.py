"""Replay historical TradingView alert JSON through the backend decision pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.config import Settings
from backend.database import SessionLocal, init_db
from backend.schemas.tradingview import TradingViewAlert
from backend.services.decision_service import DecisionService


def replay_file(path: Path, mode: str) -> dict:
    settings = Settings(environment="test", database_url="sqlite:///:memory:")
    if mode == "pine":
        settings.enable_ai_filter = False
        settings.enable_news_filter = False
    elif mode == "pine-ai":
        settings.enable_ai_filter = True
        settings.enable_news_filter = True
        settings.max_trades_per_day = 100000
        settings.max_daily_loss = 999999
    elif mode == "full":
        settings.enable_ai_filter = True
        settings.enable_news_filter = True
    else:
        raise ValueError(f"Unsupported replay mode: {mode}")

    init_db()
    service = DecisionService(settings)
    counts = {"alerts": 0, "APPROVE": 0, "REJECT": 0, "REDUCE_SIZE": 0, "WAIT": 0}
    with SessionLocal() as db:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            alert = TradingViewAlert.model_validate(json.loads(line))
            envelope = service.process(db, alert)
            counts["alerts"] += 1
            counts[envelope.response.decision] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay TradingView webhook JSONL alerts.")
    parser.add_argument("path", type=Path, help="JSONL file containing one alert payload per line")
    parser.add_argument(
        "--mode",
        choices=["pine", "pine-ai", "full"],
        default="full",
        help="Compare base Pine, Pine + AI/news, or full AI/news + risk pipeline",
    )
    args = parser.parse_args()
    print(json.dumps(replay_file(args.path, args.mode), indent=2))


if __name__ == "__main__":
    main()
