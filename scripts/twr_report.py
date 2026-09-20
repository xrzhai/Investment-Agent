"""Read-only TWR report CLI (no DB writes).

Prints a compact time-weighted return summary from snapshots + cashflows:
since-inception TWR, trailing periods (MTD / 7D / 30D / 90D / YTD), and the
worst single-period return in the measured window.

Usage:
    env -u PYTHONPATH 'C:/Users/zhaix/miniconda3/envs/work/python.exe' scripts/twr_report.py
    python scripts/twr_report.py --json          # machine-readable output
    python scripts/twr_report.py --csv out.csv   # dump the full point series
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.portfolio import PortfolioStore  # noqa: E402
from harness.portfolio.performance import compute_twr_series  # noqa: E402
from harness.settings import HarnessPaths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot-based TWR report (read-only)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--csv", type=str, default=None, help="write full series to a CSV file")
    args = parser.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
        sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    paths = HarnessPaths.discover()
    store = PortfolioStore(paths=paths)
    series = compute_twr_series(store.list_snapshots(), store.list_cashflows())

    if args.csv and series.points:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["snapshot_date", "period_return_pct", "cumulative_twr_pct"])
            for point in series.points:
                writer.writerow(
                    [point.snapshot_date, point.period_return_pct, point.cumulative_twr_pct]
                )

    if not series.points:
        print("no snapshots with positive total_value found")
        return 1

    latest = series.points[-1]
    worst = min((p for p in series.points[1:] if p.period_return_pct is not None), key=lambda p: p.period_return_pct)
    best = max((p for p in series.points[1:] if p.period_return_pct is not None), key=lambda p: p.period_return_pct)

    periods = {}
    for label, kwargs in (
        ("mtd", {"month_start": True}),
        ("7d", {"days": 7}),
        ("30d", {"days": 30}),
        ("90d", {"days": 90}),
    ):
        periods[label] = series.period_return(**kwargs)
    ytd_target = series.end_date.replace(month=1, day=1)
    ytd_base = series.cumulative_at(ytd_target)
    periods["ytd"] = (
        {"start": str(ytd_target), "twr_pct": round(series.since_inception_pct - ytd_base, 4)}
        if ytd_base is not None
        else None
    )

    if args.json:
        print(
            json.dumps(
                {
                    "since_inception": {
                        "start": str(series.start_date),
                        "end": str(series.end_date),
                        "twr_pct": series.since_inception_pct,
                    },
                    "periods": periods,
                    "worst_day": {"date": str(worst.snapshot_date), "pct": worst.period_return_pct},
                    "best_day": {"date": str(best.snapshot_date), "pct": best.period_return_pct},
                    "snapshot_count": len(series.points),
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0

    print(f"TWR 报告｜{series.start_date} → {series.end_date}（{len(series.points)} 个快照）")
    print(f"成立以来 TWR：{series.since_inception_pct:+.2f}%")
    for label in ("mtd", "ytd", "7d", "30d", "90d"):
        period = periods.get(label)
        label_display = label.upper()
        if period:
            print(f"{label_display:<4}（自 {period['start']}）：{period['twr_pct']:+.2f}%")
        else:
            print(f"{label_display:<4}：数据不足")
    print(f"最差单期：{worst.snapshot_date} {worst.period_return_pct:+.2f}%")
    print(f"最好单期：{best.snapshot_date} {best.period_return_pct:+.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
