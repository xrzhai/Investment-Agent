"""
Position Metadata Tools — CLI for reading and writing per-position analytical metadata.

Usage:
    # Write metadata for a position (called by researcher workflow)
    python app/tools/position_meta_tools.py write NVDA \\
      --target-bear 80 --target-base 140 --target-bull 200 \\
      --prob-bear 0.20 --prob-base 0.60 --prob-bull 0.20 \\
      --horizon-months 18 \\
      --sector Technology --region US --cap-style mega \\
      --growth-value growth \\
      --theme-tags '["AI基础设施","CUDA生态","数据中心"]' \\
      --risk-level high --ic-status CLEAR

    # Read all positions with metadata
    python app/tools/position_meta_tools.py read

    # Read metadata for a specific position
    python app/tools/position_meta_tools.py read NVDA
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    # Re-encode sys.argv: Git Bash passes UTF-8 bytes but Windows Python reads them as the
    # system code page (e.g. cp936). Re-encode to recover the original UTF-8 text.
    import locale
    _cp = locale.getpreferredencoding(False)
    if _cp.lower().replace("-", "") not in ("utf8", "utf-8"):
        _fixed = []
        for arg in sys.argv:
            try:
                _fixed.append(arg.encode(_cp).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                _fixed.append(arg)
        sys.argv = _fixed

from app.models.db import init_db
from app.repositories.portfolio_repo import list_positions, update_position_meta
from app.services.market_data import get_batch_prices


def _compute_cagr(target: float, current_price: float, horizon_months: int) -> float:
    """Annualised return: (target/current)^(12/horizon_months) - 1."""
    if current_price <= 0 or horizon_months <= 0:
        return 0.0
    return (target / current_price) ** (12 / horizon_months) - 1


def cmd_write(args: argparse.Namespace) -> None:
    init_db()
    symbol = args.symbol.upper()

    # Resolve current price from DB
    rows = {r.symbol: r for r in list_positions()}
    if symbol not in rows:
        print(json.dumps({"error": f"Symbol {symbol} not found in portfolio. Add it first."}))
        sys.exit(1)

    current_price = rows[symbol].current_price
    if current_price <= 0:
        print(json.dumps({"warning": f"current_price for {symbol} is 0 — CAGR cannot be computed accurately. Run portfolio_tools.py --refresh first."}))

    # Compute probability-weighted CAGR if all scenario data provided
    expected_cagr = None
    if all(v is not None for v in [
        args.target_bear, args.target_base, args.target_bull,
        args.prob_bear, args.prob_base, args.prob_bull,
        args.horizon_months
    ]) and current_price > 0:
        cagr_bear = _compute_cagr(args.target_bear, current_price, args.horizon_months)
        cagr_base = _compute_cagr(args.target_base, current_price, args.horizon_months)
        cagr_bull = _compute_cagr(args.target_bull, current_price, args.horizon_months)
        expected_cagr = (
            args.prob_bear * cagr_bear
            + args.prob_base * cagr_base
            + args.prob_bull * cagr_bull
        )

    # Parse theme_tags JSON
    theme_tags = None
    if args.theme_tags:
        try:
            parsed = json.loads(args.theme_tags)
            theme_tags = json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            print(json.dumps({"error": f"Invalid JSON for --theme-tags: {args.theme_tags}"}))
            sys.exit(1)

    meta = {
        k: v for k, v in {
            "target_bear": args.target_bear,
            "target_base": args.target_base,
            "target_bull": args.target_bull,
            "prob_bear": args.prob_bear,
            "prob_base": args.prob_base,
            "prob_bull": args.prob_bull,
            "expected_cagr": expected_cagr,
            "time_horizon_months": args.horizon_months,
            "sector": args.sector,
            "region": args.region,
            "cap_style": args.cap_style,
            "growth_value": args.growth_value,
            "theme_tags": theme_tags,
            "risk_level": args.risk_level,
            "ic_status": args.ic_status,
        }.items() if v is not None
    }

    row = update_position_meta(symbol, meta)
    if row is None:
        print(json.dumps({"error": f"Failed to update metadata for {symbol}"}))
        sys.exit(1)

    output = {
        "symbol": symbol,
        "current_price": current_price,
        "expected_cagr_pct": round(expected_cagr * 100, 2) if expected_cagr is not None else None,
        "written_fields": meta,
        "meta_updated_at": datetime.now().isoformat(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_read(args: argparse.Namespace) -> None:
    init_db()
    rows = list_positions()

    if args.symbol:
        target = args.symbol.upper()
        rows = [r for r in rows if r.symbol == target]
        if not rows:
            print(json.dumps({"error": f"Symbol {target} not found in portfolio"}))
            sys.exit(1)

    result = []
    for r in rows:
        theme_list = []
        if r.theme_tags:
            try:
                theme_list = json.loads(r.theme_tags)
            except json.JSONDecodeError:
                theme_list = [r.theme_tags]

        result.append({
            "symbol": r.symbol,
            "current_price": r.current_price,
            "expected_cagr_pct": round(r.expected_cagr * 100, 2) if r.expected_cagr is not None else None,
            "time_horizon_months": r.time_horizon_months,
            "scenarios": {
                "bear": {"target": r.target_bear, "prob": r.prob_bear},
                "base": {"target": r.target_base, "prob": r.prob_base},
                "bull": {"target": r.target_bull, "prob": r.prob_bull},
            },
            "style": {
                "sector": r.sector,
                "region": r.region,
                "cap_style": r.cap_style,
                "growth_value": r.growth_value,
            },
            "theme_tags": theme_list,
            "risk_level": r.risk_level,
            "ic_status": r.ic_status,
            "meta_updated_at": r.meta_updated_at.isoformat() if r.meta_updated_at else None,
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Position metadata read/write tool")
    subparsers = parser.add_subparsers(dest="command")

    # --- write ---
    wp = subparsers.add_parser("write", help="Write metadata for a position")
    wp.add_argument("symbol", help="Ticker symbol (e.g. NVDA)")
    wp.add_argument("--target-bear", type=float)
    wp.add_argument("--target-base", type=float)
    wp.add_argument("--target-bull", type=float)
    wp.add_argument("--prob-bear", type=float)
    wp.add_argument("--prob-base", type=float)
    wp.add_argument("--prob-bull", type=float)
    wp.add_argument("--horizon-months", type=int)
    wp.add_argument("--sector")
    wp.add_argument("--region")
    wp.add_argument("--cap-style")
    wp.add_argument("--growth-value")
    wp.add_argument("--theme-tags", help='JSON array e.g. \'["AI","semiconductor"]\'')
    wp.add_argument("--risk-level", choices=["low", "medium", "high"])
    wp.add_argument("--ic-status", choices=["CLEAR", "WATCHING", "TRIGGERED"])

    # --- read ---
    rp = subparsers.add_parser("read", help="Read metadata for all or one position")
    rp.add_argument("symbol", nargs="?", help="Optional: specific symbol to read")

    args = parser.parse_args()

    if args.command == "write":
        cmd_write(args)
    elif args.command == "read":
        cmd_read(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
