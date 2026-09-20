"""Time-weighted return (TWR) computation from snapshots and external cashflows.

Semantics (must stay consistent with ``PortfolioService.record_snapshot``):
- Only ``flow_scope == "external"`` cashflows adjust the return base; internal
  flows (dividends kept in the portfolio, internal transfers) are portfolio
  performance and must NOT be excluded.
- Flows use the event-time base-currency amount (``amount_base``), which is
  signed: deposits positive, withdrawals negative.
- External flows occurring in ``(prev_snapshot_date, snapshot_date]`` are
  treated as start-of-period additions: period return =
  ``value_end / (value_start + flows) - 1``.
- Period returns chain geometrically: cumulative TWR = prod(1 + r) - 1.
"""
from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field

from harness.portfolio.models import CashflowRecord, SnapshotRecord


class TwrPoint(BaseModel):
    snapshot_date: date
    period_return_pct: float | None = None
    cumulative_twr_pct: float


class TwrSeries(BaseModel):
    points: list[TwrPoint] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    since_inception_pct: float = 0.0

    def cumulative_at(self, target: date) -> float | None:
        """Cumulative TWR as of the last snapshot on or before ``target``."""
        chosen: TwrPoint | None = None
        for point in self.points:
            if point.snapshot_date <= target:
                chosen = point
            else:
                break
        return chosen.cumulative_twr_pct if chosen else None

    def period_return(self, *, days: int | None = None, month_start: bool = False) -> dict | None:
        """Return over the trailing window ending at the latest snapshot."""
        if not self.points or self.end_date is None:
            return None
        end = self.end_date
        target = end.replace(day=1) if month_start else end - timedelta(days=days or 0)
        base_pct = self.cumulative_at(target)
        if base_pct is None:
            return None
        return {
            "start": str(target),
            "base_snapshot_date": str(self._last_on_or_before(target).snapshot_date),
            "twr_pct": round(self.since_inception_pct - base_pct, 4),
        }

    def _last_on_or_before(self, target: date) -> TwrPoint:
        chosen = self.points[0]
        for point in self.points:
            if point.snapshot_date <= target:
                chosen = point
            else:
                break
        return chosen


def compute_twr_series(
    snapshots: list[SnapshotRecord],
    cashflows: list[CashflowRecord],
) -> TwrSeries:
    """Chain-linked TWR across snapshots, adjusted for external cashflows.

    Raises ``ValueError`` when an external flow in the measured window lacks an
    event-time base amount — matching ``record_snapshot``'s refusal to guess.
    """
    snap_points = sorted(
        (s for s in snapshots if s.total_value and s.total_value > 0),
        key=lambda s: (s.snapshot_date, s.id if s.id is not None else 0),
    )
    if not snap_points:
        return TwrSeries()

    external_flows: dict[date, float] = {}
    for flow in cashflows:
        if flow.flow_scope != "external":
            continue
        if flow.event_date < snap_points[0].snapshot_date:
            continue  # before the measurement window; record_snapshot ignores these too
        amount = flow.amount_base
        if amount is None:
            raise ValueError(
                "TWR adjustment requires event-time base amounts; "
                f"missing for flow id={flow.id} on {flow.event_date} ({flow.description[:60]})"
            )
        external_flows[flow.event_date] = external_flows.get(flow.event_date, 0.0) + float(amount)

    points: list[TwrPoint] = [TwrPoint(snapshot_date=snap_points[0].snapshot_date, cumulative_twr_pct=0.0)]
    cumulative = 1.0
    for prev, current in zip(snap_points, snap_points[1:]):
        flows = sum(
            amount for day, amount in external_flows.items() if prev.snapshot_date < day <= current.snapshot_date
        )
        base = float(prev.total_value) + flows
        if base > 0:
            period_return = (float(current.total_value) / base - 1) * 100
            cumulative *= 1 + period_return / 100
        else:
            period_return = None
        points.append(
            TwrPoint(
                snapshot_date=current.snapshot_date,
                period_return_pct=round(period_return, 6) if period_return is not None else None,
                cumulative_twr_pct=round((cumulative - 1) * 100, 6),
            )
        )

    return TwrSeries(
        points=points,
        start_date=points[0].snapshot_date,
        end_date=points[-1].snapshot_date,
        since_inception_pct=round((cumulative - 1) * 100, 4),
    )
