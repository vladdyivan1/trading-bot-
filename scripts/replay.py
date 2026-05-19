#!/usr/bin/env python3
"""Replay historical TradingView webhook payloads through the AI/risk pipeline."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal, init_db
from backend.services.replay_service import load_replay_file, replay_alerts


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay webhook alerts")
    parser.add_argument("file", help="JSON or JSONL file of alert payloads")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI filter")
    parser.add_argument("--no-risk", action="store_true", help="Use fresh risk state only")
    parser.add_argument("-o", "--output", help="Write results JSON")
    args = parser.parse_args()

    init_db()
    payloads = load_replay_file(args.file)
    db = SessionLocal()
    try:
        results = replay_alerts(
            db,
            payloads,
            enable_ai=not args.no_ai,
            enable_risk=not args.no_risk,
        )
    finally:
        db.close()

    summary = {
        "total": len(results),
        "approved": sum(1 for r in results if r.get("status") == "approved"),
        "rejected": sum(1 for r in results if r.get("status") == "rejected"),
    }
    print(json.dumps({"summary": summary, "results": results}, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps({"summary": summary, "results": results}, indent=2))


if __name__ == "__main__":
    main()
