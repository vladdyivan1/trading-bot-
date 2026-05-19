"""Dashboard analytics: PnL, win rate, rejections, time-of-day, sentiment."""
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entities import DecisionRecord, NewsSnapshot, PositionRecord


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def summary(self) -> dict:
        positions = await self._all_positions()
        closed = [p for p in positions if p.status == "closed" and p.pnl is not None]
        wins = [p for p in closed if p.pnl > 0]
        total_pnl = sum(p.pnl for p in closed)
        decisions = await self._all_decisions()
        approved = sum(1 for d in decisions if d.decision == "APPROVE")
        rejected = sum(1 for d in decisions if d.decision == "REJECT")

        equity_curve = []
        cum = 0.0
        for p in sorted(closed, key=lambda x: x.closed_at or x.opened_at):
            cum += p.pnl
            equity_curve.append(cum)
        max_dd = self._max_drawdown(equity_curve)

        return {
            "total_trades": len(closed),
            "open_positions": len([p for p in positions if p.status == "open"]),
            "win_rate": len(wins) / len(closed) if closed else 0.0,
            "total_pnl": round(total_pnl, 2),
            "max_drawdown": round(max_dd, 2),
            "decisions_approved": approved,
            "decisions_rejected": rejected,
        }

    async def rejection_breakdown(self) -> dict:
        decisions = await self._all_decisions()
        counter: Counter = Counter()
        for d in decisions:
            for r in d.rejection_reasons or []:
                counter[r] += 1
        return dict(counter.most_common(20))

    async def time_of_day_performance(self) -> dict:
        positions = await self._all_positions()
        buckets: dict[str, list[float]] = defaultdict(list)
        for p in positions:
            if p.pnl is not None and p.time_of_day_bucket:
                buckets[p.time_of_day_bucket].append(p.pnl)
        return {
            k: {
                "count": len(v),
                "total_pnl": round(sum(v), 2),
                "avg_pnl": round(sum(v) / len(v), 2) if v else 0,
            }
            for k, v in sorted(buckets.items())
        }

    async def sentiment_heatmap(self) -> dict:
        result = await self.session.execute(select(NewsSnapshot))
        snaps = list(result.scalars().all())
        grid: dict[str, Counter] = defaultdict(Counter)
        for s in snaps:
            hour = s.created_at.strftime("%H:00") if s.created_at else "unknown"
            grid[hour][s.sentiment] += 1
        return {h: dict(c) for h, c in grid.items()}

    async def regime_breakdown(self) -> dict:
        decisions = await self._all_decisions()
        counter = Counter(d.market_regime for d in decisions)
        return dict(counter)

    async def _all_positions(self) -> list[PositionRecord]:
        result = await self.session.execute(select(PositionRecord))
        return list(result.scalars().all())

    async def _all_decisions(self) -> list[DecisionRecord]:
        result = await self.session.execute(select(DecisionRecord))
        return list(result.scalars().all())

    @staticmethod
    def _max_drawdown(curve: list[float]) -> float:
        if not curve:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for v in curve:
            peak = max(peak, v)
            max_dd = max(max_dd, peak - v)
        return max_dd
