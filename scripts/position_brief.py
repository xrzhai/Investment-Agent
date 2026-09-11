"""Minimal position brief generator (runs under Windows conda Python).

Produces a compact text brief for the scheduled cron: refresh prices,
optionally record today's snapshot, and print symbol/weight/value/quantity/price.

This script must run under the Windows conda Python so it can import the
harness package. The cron orchestrator (Hermes scripts/investment_position_brief.py,
executed by WSL /usr/bin/python3) only shells out to this script and sends
the output through DingTalk.

Usage:
    python scripts/position_brief.py
    python scripts/position_brief.py --skip-refresh
    python scripts/position_brief.py --no-record
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.portfolio import PortfolioService, PortfolioStore  # noqa: E402
from harness.settings import HarnessPaths  # noqa: E402


def money_usd(value, decimals: int = 0) -> str:
    try:
        x = float(value or 0)
    except (TypeError, ValueError):
        x = 0.0
    return f"${x:,.{decimals}f}"


def pct(value) -> str:
    try:
        x = float(value or 0)
    except (TypeError, ValueError):
        x = 0.0
    return f"{x:.2f}%"


def qty(value) -> str:
    try:
        x = float(value or 0)
    except (TypeError, ValueError):
        return str(value or "-")
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}"
    return f"{x:,.4f}".rstrip("0").rstrip(".")


def local_price(position) -> str:
    price = getattr(position, "current_price", None)
    if price is None:
        return "-"
    try:
        x = float(price)
    except (TypeError, ValueError):
        return str(price)
    cur = getattr(position, "currency", None) or ""
    if cur == "USD":
        return f"${x:,.2f}"
    if cur == "CNY":
        return f"¥{x:,.2f}"
    return f"{x:,.2f} {cur}".strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-refresh", action="store_true", help="use cached prices")
    ap.add_argument("--no-record", action="store_true", help="do not record snapshot")
    args = ap.parse_args()

    paths = HarnessPaths.discover()
    store = PortfolioStore(paths=paths)
    service = PortfolioService(store, paths=paths)

    refreshed = not args.skip_refresh
    if refreshed:
        report = service.refresh_quotes()
        if report.errors:
            print("\n".join(report.errors), file=sys.stderr)
            return 1

    recorded = False
    if not args.no_record:
        note = f"scheduled position brief {datetime.now().date().isoformat()} by Hermes"
        service.record_snapshot(notes=note, source_ref="position_brief_cron")
        recorded = True

    state = service.get_state()
    positions = [p for p in state.positions if not p.symbol.startswith("CASH_")]
    positions.sort(key=lambda p: float(p.weight_pct or 0), reverse=True)

    status_bits = ["已刷新" if refreshed else "缓存价格"]
    status_bits.append("已记录快照" if recorded else "未记录快照")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"持仓占比｜{now}",
        f"口径：{' / '.join(status_bits)}",
        f"总资产：{money_usd(state.total_value, 2)}｜持仓数：{len(positions)}",
        "",
        "持仓明细：",
    ]
    for i, p in enumerate(positions, 1):
        lines.append(
            f"{i:02d}. {p.symbol}: {pct(p.weight_pct)}｜{money_usd(p.base_market_value, 0)}｜"
            f"数量 {qty(p.quantity)}｜价 {local_price(p)}"
        )
    print("\n".join(lines).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
