"""
Option Tools — standalone executable script for sold put workflows.

Usage:
    python app/tools/option_tools.py summary [--refresh]
    python app/tools/option_tools.py list [--status open]
    python app/tools/option_tools.py open-put SYMBOL EXPIRY STRIKE CONTRACTS --premium 11.53
    python app/tools/option_tools.py assign ID [--date YYYY-MM-DD] [--price 40]
    python app/tools/option_tools.py expire ID [--date YYYY-MM-DD]
    python app/tools/option_tools.py close ID --cost-to-close 1.25 [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.db import init_db
from app.repositories.options_repo import (
    compute_open_put_exposure,
    create_option_contract,
    get_option_contract,
    list_option_contracts,
    mark_option_assigned,
    mark_option_closed,
    mark_option_expired,
)
from app.repositories.portfolio_repo import list_positions, update_price
from app.services.market_data import get_batch_prices


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _refresh_portfolio_prices() -> None:
    rows = list_positions()
    if not rows:
        return
    prices = get_batch_prices([r.symbol for r in rows])
    for sym, price in prices.items():
        if price is not None:
            update_price(sym, price)


def get_option_summary(refresh: bool = False) -> dict:
    init_db()
    if refresh:
        _refresh_portfolio_prices()
    spot_rows = list_positions()
    from app.engines.portfolio_engine import compute_positions

    positions = compute_positions(spot_rows)
    total_value_usd = round(sum(p.base_market_value for p in positions), 2)
    option_rows = list_option_contracts(status="open")
    exposure = compute_open_put_exposure(
        spot_positions=positions,
        option_rows=option_rows,
        total_portfolio_value_usd=total_value_usd,
        fetch_spot_prices=True,
    )
    return {
        "timestamp": datetime.now().isoformat(),
        "open_contract_count": exposure["contract_count"],
        "options_exposure": exposure,
    }


def list_contracts(status: str | None = None) -> dict:
    init_db()
    rows = list_option_contracts(status=status)
    return {
        "contracts": [
            {
                "id": r.id,
                "underlying_symbol": r.underlying_symbol,
                "status": r.status,
                "contracts": r.contracts,
                "strike": r.strike,
                "expiry_date": str(r.expiry_date),
                "premium_per_share": r.premium_per_share,
                "premium_total": r.premium_total,
                "reserved_cash": r.reserved_cash,
                "effective_entry_if_assigned": r.effective_entry_if_assigned,
                "intent": r.intent,
                "notes": r.notes,
            }
            for r in rows
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sold put management tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary")
    p_summary.add_argument("--refresh", action="store_true")

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default=None)

    p_open = sub.add_parser("open-put")
    p_open.add_argument("symbol")
    p_open.add_argument("expiry")
    p_open.add_argument("strike", type=float)
    p_open.add_argument("contracts", type=int)
    p_open.add_argument("--premium", required=True, type=float)
    p_open.add_argument("--opened-date", default=None)
    p_open.add_argument("--fees", default=0.0, type=float)
    p_open.add_argument("--intent", default="lower_price_entry")
    p_open.add_argument("--notes", default="")
    p_open.add_argument("--decision-file", default="")

    p_assign = sub.add_parser("assign")
    p_assign.add_argument("contract_id", type=int)
    p_assign.add_argument("--date", default=None)
    p_assign.add_argument("--price", default=None, type=float)
    p_assign.add_argument("--notes", default="")
    p_assign.add_argument("--apply-to-spot", action="store_true")

    p_expire = sub.add_parser("expire")
    p_expire.add_argument("contract_id", type=int)
    p_expire.add_argument("--date", default=None)
    p_expire.add_argument("--notes", default="")

    p_close = sub.add_parser("close")
    p_close.add_argument("contract_id", type=int)
    p_close.add_argument("--cost-to-close", required=True, type=float)
    p_close.add_argument("--date", default=None)
    p_close.add_argument("--notes", default="")

    args = parser.parse_args()

    if args.command == "summary":
        print(json.dumps(get_option_summary(refresh=args.refresh), indent=2, ensure_ascii=False))
        return

    if args.command == "list":
        print(json.dumps(list_contracts(status=args.status), indent=2, ensure_ascii=False))
        return

    init_db()
    if args.command == "open-put":
        row = create_option_contract(
            underlying_symbol=args.symbol,
            expiry_date=_parse_date(args.expiry),
            strike=args.strike,
            contracts=args.contracts,
            premium_per_share=args.premium,
            opened_date=_parse_date(args.opened_date),
            fees=args.fees,
            intent=args.intent,
            notes=args.notes,
            linked_decision_file=args.decision_file,
        )
        print(json.dumps({
            "ok": True,
            "id": row.id,
            "underlying_symbol": row.underlying_symbol,
            "contracts": row.contracts,
            "reserved_cash": row.reserved_cash,
            "effective_entry_if_assigned": row.effective_entry_if_assigned,
        }, indent=2, ensure_ascii=False))
        return

    if args.command == "assign":
        row = mark_option_assigned(
            args.contract_id,
            assigned_date=_parse_date(args.date),
            assignment_price=args.price,
            notes=args.notes,
            apply_to_spot=args.apply_to_spot,
        )
    elif args.command == "expire":
        row = mark_option_expired(args.contract_id, expired_date=_parse_date(args.date), notes=args.notes)
    elif args.command == "close":
        row = mark_option_closed(
            args.contract_id,
            closed_date=_parse_date(args.date),
            realized_cost_to_close=args.cost_to_close,
            notes=args.notes,
        )
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    print(json.dumps({
        "ok": True,
        "id": row.id,
        "status": row.status,
        "underlying_symbol": row.underlying_symbol,
        "realized_premium": row.realized_premium,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
