"""Refresh portfolio quotes + FX and print portfolio state.

Thin CLI wrapper over the harness's built-in market-data bridge. All logic
lives in ``harness.portfolio.MarketDataClient`` / ``PortfolioService.refresh_quotes``;
this script only wires it to a terminal-friendly output.

Usage:
    python scripts/refresh_quotes.py            # pull + persist + show state
    python scripts/refresh_quotes.py --dry-run  # pull only, do not persist
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.portfolio import MarketDataClient, PortfolioService, PortfolioStore  # noqa: E402
from harness.settings import HarnessPaths  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="pull prices but do not persist")
    args = ap.parse_args()

    paths = HarnessPaths.discover()
    store = PortfolioStore(paths=paths)
    service = PortfolioService(store, paths=paths)

    if args.dry_run:
        client = MarketDataClient()
        positions = store.list_positions()
        symbols = [p.symbol for p in positions if not p.symbol.startswith("CASH_")]
        currencies = sorted({p.currency for p in positions if p.currency and not p.currency.startswith("CASH_")})
        report = client.refresh_portfolio(symbols, fx_pairs=[(c, "USD") for c in currencies if c.upper() != "USD"])
    else:
        report = service.refresh_quotes()

    for obs in report.observed:
        print(f"  {obs.symbol:14s} {obs.price:>12.4f} {obs.currency:5s} <- {obs.source}")

    if args.dry_run:
        print("\n[dry-run] not persisting")
        return 0

    print("\n--- portfolio state ---")
    state = service.get_state()
    print(f"as_of={state.as_of}")
    print(f"total_value={state.total_value}  cash={state.cash_value} ({state.cash_pct:.2f}%)")
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
    if report.errors:
        print("\npull errors:")
        for e in report.errors:
            print(f"  {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
