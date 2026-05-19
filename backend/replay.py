from __future__ import annotations

import argparse
import json

from backend.models import SessionLocal
from backend.services.replay_service import ReplayService


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay historical TradingView webhook events through AI/risk filters.")
    parser.add_argument("--limit", type=int, default=500, help="Max historical events to replay.")
    parser.add_argument("--out", type=str, default="docs/replay_report.json", help="Output path for replay report.")
    args = parser.parse_args()

    replay = ReplayService()
    with SessionLocal() as db:
        report = replay.run(db, limit=args.limit)

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"Replay report written to {args.out}")


if __name__ == "__main__":
    main()
