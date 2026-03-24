"""
Portfolio Tools — standalone executable script for Claude Code.

Usage:
    python app/tools/portfolio_tools.py
    python app/tools/portfolio_tools.py --refresh

Outputs JSON to stdout. All monetary totals are in base currency (USD).
Mixed-currency portfolios are supported: A-share positions are converted via CNY/USD FX rate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engines.portfolio_engine import compute_positions
from app.repositories.portfolio_repo import list_positions, update_price
from app.services.market_data import get_batch_prices, get_fx_rate
from app.services.profile_service import load_profile


def get_portfolio_state(refresh_prices: bool = False) -> dict:
    """
    Return current portfolio state as a dict ready for JSON serialisation.
    If refresh_prices=True, fetches latest prices from market data sources first.
    All monetary totals are in USD (base currency).
    """
    rows = list_positions()
    if not rows:
        return {
            "timestamp": datetime.now().isoformat(),
            "base_currency": "USD",
            "total_value_usd": 0.0,
            "positions": [],
            "price_source": "none",
            "warning": "No positions found. Add positions with: python run.py portfolio add <SYMBOL> <QTY> --cost <PRICE>",
        }

    if refresh_prices:
        symbols = [r.symbol for r in rows]
        prices = get_batch_prices(symbols)
        for sym, price in prices.items():
            if price is not None:
                update_price(sym, price)
        # Reload rows with updated prices
        rows = list_positions()
        price_source = "live"
    else:
        price_source = "cached"

    # Fetch FX rate once for efficiency
    fx_rate = get_fx_rate("CNY", "USD")

    positions = compute_positions(rows, fx_rate_cny_usd=fx_rate)

    total_usd = sum(p.base_market_value for p in positions)
    # Cost basis converted to USD for total PnL
    total_cost_usd = sum(p.avg_cost * p.quantity * p.fx_rate_to_base for p in positions)
    total_pnl = total_usd - total_cost_usd
    total_pnl_pct = (total_pnl / total_cost_usd * 100) if total_cost_usd else 0.0

    profile = load_profile()

    # FX info
    has_cn = any(p.market == "CN_A" for p in positions)
    fx_info = None
    if has_cn:
        cn_pos = next((p for p in positions if p.market == "CN_A"), None)
        fx_info = {
            "cny_usd": round(fx_rate, 6) if fx_rate else None,
            "stale": cn_pos.fx_stale if cn_pos else False,
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "base_currency": "USD",
        "price_source": price_source,
        "total_value_usd": round(total_usd, 2),
        "total_cost_usd": round(total_cost_usd, 2),
        "total_unrealized_pnl_usd": round(total_pnl, 2),
        "total_unrealized_pnl_pct": round(total_pnl_pct, 2),
        "position_count": len(positions),
        "fx": fx_info,
        "investor_profile": {
            "style": profile.style,
            "risk_tolerance": profile.risk_tolerance,
            "max_position_weight_pct": round(profile.max_position_weight * 100, 1),
            "max_drawdown_tolerance_pct": round(profile.max_drawdown_tolerance * 100, 1),
        },
        "positions": [
            {
                "symbol": p.symbol,
                "market": p.market,
                "currency": p.currency,
                "quantity": p.quantity,
                "avg_cost": round(p.avg_cost, 4),
                "local_price": round(p.local_price, 4) if p.local_price else None,
                "local_market_value": round(p.local_market_value, 2),
                "fx_rate_to_usd": round(p.fx_rate_to_base, 6),
                "base_market_value_usd": round(p.base_market_value, 2),
                "unrealized_pnl_local": round(p.unrealized_pnl, 2),
                "unrealized_pnl_pct": round(p.unrealized_pnl_pct, 2),
                "weight_pct": round(p.weight, 2),
                "fx_stale": p.fx_stale,
                "price_source": p.price_source,
            }
            for p in sorted(positions, key=lambda x: x.base_market_value, reverse=True)
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get portfolio state as JSON")
    parser.add_argument("--refresh", action="store_true", help="Fetch latest prices from market data")
    args = parser.parse_args()

    result = get_portfolio_state(refresh_prices=args.refresh)
    print(json.dumps(result, indent=2, ensure_ascii=False))
