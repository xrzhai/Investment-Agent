"""
P&L Tools — standalone executable script for agent workflows.

Usage:
    python app/tools/pnl_tools.py --record [--notes TEXT]
        Record current portfolio value as a P&L snapshot (uses cached prices).

    python app/tools/pnl_tools.py --cashflow AMOUNT [--desc TEXT]
        Record a deposit (positive) or withdrawal (negative) event in USD.
        Automatically records a snapshot before the cashflow for accurate TWR.

    python app/tools/pnl_tools.py --curve [--days N]
        Display ASCII line chart of capital curve (USD) and cumulative TWR (%).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Force UTF-8 output on Windows to handle plotext's Unicode drawing characters
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.db import init_db
from app.repositories.portfolio_repo import (
    list_cashflows,
    list_snapshots_asc,
    save_cashflow,
    upsert_pnl_snapshot,
)
from app.tools.portfolio_tools import get_portfolio_state


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _cash_value_from_positions(positions: list[dict]) -> float:
    return round(
        sum(
            float(p.get("base_market_value_usd") or 0.0)
            for p in positions
            if str(p.get("symbol", "")).startswith("CASH")
        ),
        2,
    )


def _top_position_weight(positions: list[dict]) -> float:
    if not positions:
        return 0.0
    return round(max(float(p.get("weight_pct") or 0.0) for p in positions), 2)


def _daily_return_pct(total_value: float, snapshot_date: date, snapshots, cashflows) -> float:
    previous = None
    for snap in snapshots:
        if _as_date(snap.snapshot_date) < snapshot_date:
            previous = snap
    if previous is None or not previous.total_value:
        return 0.0

    prev_date = _as_date(previous.snapshot_date)
    cashflow_total = sum(
        float(c.amount_usd)
        for c in cashflows
        if prev_date < _as_date(c.event_date) <= snapshot_date
    )
    return round(((total_value - cashflow_total) / float(previous.total_value) - 1) * 100, 2)


def _max_drawdown_pct(total_value: float, snapshot_date: date, snapshots) -> float:
    values = [
        float(s.total_value)
        for s in snapshots
        if _as_date(s.snapshot_date) < snapshot_date and float(s.total_value) > 0
    ]
    if total_value > 0:
        values.append(float(total_value))
    if not values:
        return 0.0

    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            drawdown = (value / peak - 1) * 100
            max_drawdown = min(max_drawdown, drawdown)
    return round(max_drawdown, 2)


def _record_snapshot(notes: str = "") -> float:
    """Record today's portfolio value. Returns total_value_usd."""
    state = get_portfolio_state(refresh_prices=False)
    total = state.get("total_value_usd", 0.0)
    positions = state.get("positions", [])
    snapshots = list_snapshots_asc()
    cashflows = list_cashflows()
    snapshot_date = date.today()

    upsert_pnl_snapshot(
        total,
        notes=notes,
        cash=_cash_value_from_positions(positions),
        daily_return_pct=_daily_return_pct(total, snapshot_date, snapshots, cashflows),
        max_drawdown_pct=_max_drawdown_pct(total, snapshot_date, snapshots),
        top_position_weight=_top_position_weight(positions),
        positions_json=json.dumps(positions, ensure_ascii=False, default=str),
    )
    return total


def _compute_twr(snapshots, cashflows) -> list[float]:
    """
    Compute cumulative TWR series aligned with the snapshots list.

    Returns a list of cumulative TWR values (as percentages) with the same
    length as snapshots. The first element is always 0.0.
    """
    if len(snapshots) < 2:
        return [0.0] * len(snapshots)

    twr_factor = 1.0
    results = [0.0]  # first snapshot is base = 0%

    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        # Cashflows occurring strictly after prev date and on or before curr date
        cf = sum(
            c.amount_usd for c in cashflows
            if prev.snapshot_date < c.event_date <= curr.snapshot_date
        )
        denominator = prev.total_value
        if denominator == 0:
            results.append(results[-1])
            continue
        period_factor = (curr.total_value - cf) / denominator
        twr_factor *= period_factor
        results.append(round((twr_factor - 1) * 100, 2))

    return results


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_record(notes: str) -> None:
    init_db()
    total = _record_snapshot(notes=notes)
    print(f"[OK] Snapshot recorded: ${total:,.2f} USD  (notes: {notes or '-'})")


def cmd_cashflow(amount: float, desc: str) -> None:
    init_db()
    # Record a snapshot right before the cashflow for clean TWR sub-period boundary
    _record_snapshot(notes="pre-cashflow")
    today = date.today()
    save_cashflow(today, amount, description=desc)
    direction = "deposit" if amount >= 0 else "withdrawal"
    print(f"[OK] Cashflow recorded: {direction} ${abs(amount):,.2f} USD  ({desc or '-'})")
    print("     Pre-cashflow snapshot also recorded for accurate TWR.")


def cmd_curve(days: int | None) -> None:
    init_db()
    try:
        import plotext as plt
    except ImportError:
        print("[ERROR] plotext not installed. Run: pip install plotext")
        sys.exit(1)

    snapshots = list_snapshots_asc()
    cashflows = list_cashflows()

    if len(snapshots) < 2:
        print("[WARN] Not enough data to plot (need >= 2 snapshots).")
        print("       Record snapshots manually or run a review workflow to start accumulating data.")
        return

    # Filter by --days if specified
    if days:
        cutoff = date.today() - timedelta(days=days)
        snapshots = [s for s in snapshots if s.snapshot_date >= cutoff]
        if len(snapshots) < 2:
            print(f"[WARN] Less than 2 snapshots in the last {days} days.")
            return

    twr_series = _compute_twr(snapshots, cashflows)
    dates_str = [str(s.snapshot_date) for s in snapshots]
    values = [s.total_value for s in snapshots]
    x = list(range(len(snapshots)))

    # Plotext: two subplots stacked vertically
    plt.clf()
    plt.subplots(2, 1)

    # Top: capital curve (USD)
    plt.subplot(1, 1)
    plt.plot(x, values, label="Capital (USD)", color="cyan")
    plt.title("Portfolio Capital Curve (USD)")
    plt.ylabel("USD")
    # Label first and last date on x-axis
    if len(x) >= 2:
        plt.xticks([x[0], x[-1]], [dates_str[0], dates_str[-1]])

    # Bottom: cumulative TWR (%)
    plt.subplot(2, 1)
    plt.plot(x, twr_series, label="Cumulative TWR (%)", color="green")
    plt.title("Cumulative Time-Weighted Return (%)")
    plt.ylabel("%")
    if len(x) >= 2:
        plt.xticks([x[0], x[-1]], [dates_str[0], dates_str[-1]])

    plt.show()

    # Summary line
    first_val = values[0]
    last_val = values[-1]
    last_twr = twr_series[-1]
    print(f"\n  Period: {dates_str[0]} → {dates_str[-1]}  |  "
          f"Capital: ${first_val:,.0f} → ${last_val:,.0f}  |  "
          f"TWR: {last_twr:+.2f}%")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P&L curve recording tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", action="store_true", help="Record today's portfolio value as snapshot")
    group.add_argument("--cashflow", type=float, metavar="AMOUNT", help="Record cashflow event (USD, positive=deposit)")
    group.add_argument("--curve", action="store_true", help="Display ASCII P&L curve")

    parser.add_argument("--notes", default="manual", help="Notes/source tag for --record")
    parser.add_argument("--desc", default="", help="Description for --cashflow")
    parser.add_argument("--days", type=int, default=None, help="Limit --curve to last N days")

    args = parser.parse_args()

    if args.record:
        cmd_record(notes=args.notes)
    elif args.cashflow is not None:
        cmd_cashflow(amount=args.cashflow, desc=args.desc)
    elif args.curve:
        cmd_curve(days=args.days)
