"""
CN Market Data Tools — standalone executable for Claude Code workflows.

Fetches A-share data via JQData (聚宽) and outputs JSON to stdout.
Requires JQ_USER and JQ_PASS environment variables.

Usage:
    python app/tools/cn_market_data_tools.py 600519.SH
    python app/tools/cn_market_data_tools.py 600519.SH --mode fundamentals
    python app/tools/cn_market_data_tools.py 600519.SH --mode history --days 90
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.jqdata_provider import (
    get_price, get_fundamentals, get_consensus_estimates, get_price_history,
    get_security_info, is_cn_a_symbol
)


def get_full_snapshot(symbol: str, history_days: int = 60) -> dict:
    """Full data snapshot for researcher workflow: price + fundamentals + history summary."""
    result: dict = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "data_source": "jqdata",
    }

    # Security info
    info = get_security_info(symbol)
    result["security_info"] = info

    # Current price
    price = get_price(symbol)
    result["current_price_cny"] = price

    # Fundamentals (full fiscal-year data via statDate)
    fundamentals = get_fundamentals(symbol)
    result["fundamentals"] = fundamentals

    # Consensus estimates + derived forward P/E
    consensus = get_consensus_estimates(symbol)
    if consensus and price:
        for est in consensus.get("estimates", []):
            if est.get("eps_avg") and est["eps_avg"] > 0:
                est["forward_pe"] = round(price / est["eps_avg"], 1)
    result["consensus_estimates"] = consensus if consensus else None

    # Price history summary
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
    hist_df = get_price_history(symbol, start=start, end=end)
    if hist_df is not None and not hist_df.empty:
        result["price_history_summary"] = {
            "period": f"{start} to {end}",
            "trading_days": len(hist_df),
            "start_price": round(float(hist_df["close"].iloc[0]), 2),
            "end_price": round(float(hist_df["close"].iloc[-1]), 2),
            "high": round(float(hist_df["high"].max()), 2),
            "low": round(float(hist_df["low"].min()), 2),
            "price_change_pct": round(
                (float(hist_df["close"].iloc[-1]) / float(hist_df["close"].iloc[0]) - 1) * 100, 2
            ),
            "avg_volume": round(float(hist_df["volume"].mean()), 0) if "volume" in hist_df else None,
        }
    else:
        result["price_history_summary"] = None

    return result


def get_price_only(symbol: str) -> dict:
    price = get_price(symbol)
    return {
        "symbol": symbol,
        "current_price_cny": price,
        "timestamp": datetime.now().isoformat(),
        "data_source": "jqdata",
    }


def get_fundamentals_only(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "fundamentals": get_fundamentals(symbol),
        "timestamp": datetime.now().isoformat(),
        "data_source": "jqdata",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch A-share data via JQData")
    parser.add_argument("symbol", help="Canonical A-share symbol, e.g. 600519.SH")
    parser.add_argument(
        "--mode",
        choices=["full", "price", "fundamentals", "history"],
        default="full",
        help="Data mode (default: full)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="History days for full/history mode (default: 60)",
    )
    args = parser.parse_args()

    if not is_cn_a_symbol(args.symbol):
        print(json.dumps({"error": f"Not a valid A-share symbol: {args.symbol}"}))
        sys.exit(1)

    if args.mode == "price":
        output = get_price_only(args.symbol)
    elif args.mode == "fundamentals":
        output = get_fundamentals_only(args.symbol)
    elif args.mode == "history":
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        hist_df = get_price_history(args.symbol, start=start, end=end)
        if hist_df is not None and not hist_df.empty:
            records = hist_df.reset_index().rename(columns={"index": "date"})
            output = {
                "symbol": args.symbol,
                "period": f"{start} to {end}",
                "records": records.to_dict(orient="records"),
            }
        else:
            output = {"symbol": args.symbol, "error": "No history data available"}
    else:  # full
        output = get_full_snapshot(args.symbol, history_days=args.days)

    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
