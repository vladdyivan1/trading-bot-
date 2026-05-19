#!/usr/bin/env python3
"""
Replay historical TradingView webhook payloads through AI + risk filters.

Usage:
  python -m backend.scripts.replay --db ./data/scalper.db
  python -m backend.scripts.replay --mode pine_only|pine_ai|pine_ai_risk
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.models.entities import AlertRecord, Base
from backend.schemas.alerts import TradingViewAlert
from backend.services.alert_store import AlertStore
from backend.services.regime_classifier import classify_regime
from backend.services.risk_engine import RiskEngine
from ai.llm_decision import RuleBasedDecisionEngine
from ai.news_providers import MockNewsProvider


async def replay(mode: str, database_url: str) -> dict:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    settings = get_settings()
    decision_engine = RuleBasedDecisionEngine()
    news = MockNewsProvider(scenario="neutral")
    risk = RiskEngine(settings)

    stats = {
        "total": 0,
        "approve": 0,
        "reject": 0,
        "wait": 0,
        "reduce": 0,
        "mode": mode,
    }

    async with factory() as session:
        result = await session.execute(select(AlertRecord).order_by(AlertRecord.received_at))
        alerts = list(result.scalars().all())

        for rec in alerts:
            stats["total"] += 1
            payload = rec.payload
            alert = TradingViewAlert.model_validate({**payload, "raw_payload": payload})
            regime = classify_regime(alert)

            if mode == "pine_only":
                action = "APPROVE" if alert.is_bullish or alert.is_bearish else "WAIT"
            else:
                bundle = await news.fetch_headlines("SPY") if mode != "pine_only" else None
                headlines = bundle.headlines if bundle else []
                decision = await decision_engine.evaluate(
                    alert, headlines, regime, bundle.event_risk if bundle else False
                )
                if mode == "pine_ai_risk":
                    decision, _ = risk.evaluate(alert, decision, rec.alert_id)
                action = decision.decision.value

            stats[action.lower()] = stats.get(action.lower(), 0) + 1

    await engine.dispose()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Replay alerts through filters")
    parser.add_argument(
        "--mode",
        choices=["pine_only", "pine_ai", "pine_ai_risk"],
        default="pine_ai_risk",
    )
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    url = args.db or get_settings().database_url
    stats = asyncio.run(replay(args.mode, url))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
