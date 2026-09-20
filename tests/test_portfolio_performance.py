from __future__ import annotations

from datetime import date, datetime, timezone

from harness.portfolio.models import CashflowRecord, SnapshotRecord
from harness.portfolio.performance import compute_twr_series


def _snap(day: date, value: float, sid: int | None = None) -> SnapshotRecord:
    return SnapshotRecord(snapshot_date=day, total_value=value, id=sid)


def _flow(
    day: date,
    amount: float,
    *,
    scope: str = "external",
    currency: str = "USD",
    amount_base: float | None = None,
) -> CashflowRecord:
    return CashflowRecord(
        event_date=day,
        amount_usd=amount if currency == "USD" else 0.0,
        currency=currency,
        amount_base=amount_base if amount_base is not None else (amount if currency == "USD" else None),
        flow_scope=scope,
        flow_type="deposit",
        description="test flow",
    )


def test_twr_chains_periods_and_adjusts_external_flows():
    snaps = [_snap(date(2026, 1, 1), 1000, 1), _snap(date(2026, 1, 8), 1100, 2), _snap(date(2026, 1, 15), 1210, 3)]
    # Convention (same as record_snapshot): flows in (prev, current] count as
    # start-of-period additions. Flow on 1/8 -> period1 base = 1000+100 = 1100.
    # period1: 1100/1100-1 = 0%; period2: 1210/1100-1 = +10%
    flows = [_flow(date(2026, 1, 8), 100)]
    series = compute_twr_series(snaps, flows)
    assert series.points[1].period_return_pct == 0.0
    assert series.points[2].period_return_pct == 10.0
    assert abs(series.points[2].cumulative_twr_pct - 10.0) < 1e-6
    assert series.since_inception_pct == series.points[-1].cumulative_twr_pct
    assert series.period_return(days=7)["twr_pct"] == series.points[2].cumulative_twr_pct - series.points[1].cumulative_twr_pct


def test_internal_flows_are_not_excluded():
    # dividend (internal) kept in portfolio: must NOT reduce the base
    snaps = [_snap(date(2026, 2, 1), 1000, 1), _snap(date(2026, 2, 2), 1010, 2)]
    flows = [_flow(date(2026, 2, 2), 10, scope="internal")]
    series = compute_twr_series(snaps, flows)
    assert series.points[1].period_return_pct == 1.0


def test_withdrawal_is_negative_flow():
    snaps = [_snap(date(2026, 3, 1), 1000, 1), _snap(date(2026, 3, 2), 950, 2)]
    flows = [_flow(date(2026, 3, 2), -50)]
    series = compute_twr_series(snaps, flows)
    assert series.points[1].period_return_pct == 0.0


def test_flow_before_first_snapshot_is_ignored():
    snaps = [_snap(date(2026, 4, 1), 1000, 1), _snap(date(2026, 4, 2), 1010, 2)]
    flows = [_flow(date(2026, 3, 15), 500)]
    series = compute_twr_series(snaps, flows)
    assert series.points[1].period_return_pct == 1.0


def test_missing_base_amount_raises():
    snaps = [_snap(date(2026, 5, 1), 1000, 1), _snap(date(2026, 5, 2), 1010, 2)]
    flows = [_flow(date(2026, 5, 2), 100, currency="CNY", amount_base=None)]
    try:
        compute_twr_series(snaps, flows)
    except ValueError as exc:
        assert "base amounts" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing amount_base")


def test_period_return_month_start():
    snaps = [
        _snap(date(2026, 6, 20), 1000, 1),
        _snap(date(2026, 7, 1), 1100, 2),
        _snap(date(2026, 7, 10), 1200, 3),
    ]
    series = compute_twr_series(snaps, [])
    mtd = series.period_return(month_start=True)
    assert mtd is not None and mtd["twr_pct"] == series.points[-1].cumulative_twr_pct - series.points[1].cumulative_twr_pct
