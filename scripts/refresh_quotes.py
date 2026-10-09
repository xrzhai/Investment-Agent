"""Refresh portfolio quotes + FX, print portfolio state, and record today's snapshot.

Thin CLI wrapper over the harness's built-in market-data bridge. All logic
lives in ``harness.portfolio.MarketDataClient`` / ``PortfolioService``;
this script only wires it to a terminal-friendly output.

This is the single supported entry point for refreshing portfolio quotes.
A snapshot is recorded by default when every quote pulled cleanly and the
valuation is complete; same-day reruns overwrite that day's snapshot.

Usage:
    python scripts/refresh_quotes.py              # pull + persist + record snapshot
    python scripts/refresh_quotes.py --no-record  # pull + persist, no snapshot
    python scripts/refresh_quotes.py --dry-run    # pull only, do not persist
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.portfolio import MarketDataClient, PortfolioService, PortfolioStore  # noqa: E402
from harness.settings import HarnessPaths  # noqa: E402


def main(
    argv: list[str] | None = None,
    *,
    paths: HarnessPaths | None = None,
    client: MarketDataClient | None = None,
) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="pull prices but do not persist")
    ap.add_argument("--no-record", action="store_true", help="do not record today's snapshot")
    # Recording is now the default; --record is still accepted so older callers keep working.
    ap.add_argument("--record", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    paths = paths or HarnessPaths.discover()
    store = PortfolioStore(paths=paths)
    service = PortfolioService(store, paths=paths)

    if args.dry_run:
        client = client or MarketDataClient()
        positions = store.list_positions()
        symbols = [p.symbol for p in positions if not p.symbol.startswith("CASH_")]
        currencies = sorted({p.currency for p in positions if p.currency and not p.currency.startswith("CASH_")})
        report = client.refresh_portfolio(symbols, fx_pairs=[(c, "USD") for c in currencies if c.upper() != "USD"])
    else:
        report = service.refresh_quotes(client=client)

    for obs in report.observed:
        print(f"  {obs.symbol:14s} {obs.price:>12.4f} {obs.currency:5s} <- {obs.source}")

    if args.dry_run:
        print("\n[dry-run] not persisting")
        return 0

    print("\n--- portfolio state ---")
    state = service.get_state()
    print(f"as_of={state.as_of}")
    cash_pct_text = f"{state.cash_pct:.2f}%" if state.cash_pct is not None else "N/A"
    print(f"total_value={state.total_value}  cash={state.cash_value} ({cash_pct_text})")
    print(f"valuation_complete={state.valuation_complete}  priced={state.priced_position_count}/{state.held_position_count}")
    if state.warnings:
        for w in state.warnings:
            print(f"  WARN: {w}")
    print("\nper-position:")
    for v in state.positions:
        if v.symbol.startswith("CASH_"):
            continue
        flags = ",".join(v.data_quality) if v.data_quality else "-"
        print(f"  {v.symbol:10s} {v.quantity:>10.3f} {v.current_price if v.current_price else 0:>12.4f} "
              f"wt={v.weight_pct if v.weight_pct is not None else float('nan'):>7.2f}%  q=[{flags}]")

    if args.no_record:
        print("\n[record] skipped (--no-record)")
    elif report.errors:
        # A failed pull can leave an older quote in place; do not freeze it into today's snapshot.
        print("\n[record] SKIPPED: some quotes failed to refresh; fix the errors below, then rerun")
    elif not state.valuation_complete:
        print("\n[record] SKIPPED: portfolio valuation incomplete; fix missing prices/FX, then rerun")
    else:
        snapshot_day = state.as_of.astimezone(timezone(timedelta(hours=8))).date()
        snapshot, _ = service.record_snapshot(
            snapshot_date=snapshot_day,
            notes=f"refresh_quotes {snapshot_day}",
            source_ref="refresh_quotes",
        )
        print(f"\n[record] snapshot {snapshot.snapshot_date} saved  "
              f"total={snapshot.total_value} cash={snapshot.cash} "
              f"daily_return={snapshot.daily_return_pct}% max_dd={snapshot.max_drawdown_pct}%")

    if report.errors:
        print("\npull errors:")
        for e in report.errors:
            print(f"  {e}")
        return 1
    if not args.no_record and not state.valuation_complete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
