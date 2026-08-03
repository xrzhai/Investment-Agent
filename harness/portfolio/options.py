from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable


def derive_open_put_metrics(
    *,
    strike: float,
    contracts: int,
    premium_per_share: float,
    shares_per_contract: int = 100,
    fees: float = 0.0,
) -> dict[str, float | int]:
    if strike <= 0:
        raise ValueError("strike must be positive")
    contract_count = abs(int(contracts))
    if contract_count <= 0:
        raise ValueError("contracts must be non-zero")
    if shares_per_contract <= 0:
        raise ValueError("shares_per_contract must be positive")
    if premium_per_share < 0 or fees < 0:
        raise ValueError("premium and fees cannot be negative")

    total_shares = contract_count * shares_per_contract
    premium_total = round(total_shares * premium_per_share, 2)
    reserved_cash = round(total_shares * strike, 2)
    net_cash_obligation = round(reserved_cash - premium_total + fees, 2)
    return {
        "contract_count": contract_count,
        "total_shares": total_shares,
        "premium_total": premium_total,
        "reserved_cash": reserved_cash,
        "net_cash_obligation": net_cash_obligation,
        "effective_entry_if_assigned": round(net_cash_obligation / total_shares, 4),
    }


def compute_open_put_exposure(
    *,
    positions: Iterable,
    option_contracts: Iterable,
    portfolio_total_value: float,
) -> dict:
    positions = list(positions)
    options = [row for row in option_contracts if getattr(row, "status", "open") == "open"]
    position_by_symbol = {str(getattr(row, "symbol", "")).upper(): row for row in positions}
    cash_by_currency: dict[str, float] = defaultdict(float)
    for row in positions:
        symbol = str(getattr(row, "symbol", "")).upper()
        if symbol.startswith("CASH_"):
            currency = symbol.removeprefix("CASH_")
            cash_by_currency[currency] += float(getattr(row, "quantity", 0.0) or 0.0)

    reserved_by_currency: dict[str, float] = defaultdict(float)
    contracts_out: list[dict] = []
    for row in options:
        metrics = derive_open_put_metrics(
            strike=float(row.strike),
            contracts=int(row.contracts),
            premium_per_share=float(row.premium_per_share or 0.0),
            shares_per_contract=int(row.shares_per_contract),
            fees=float(row.fees or 0.0),
        )
        symbol = row.underlying_symbol.upper()
        currency = str(row.currency or "USD").upper()
        spot = position_by_symbol.get(symbol)
        current_qty = float(getattr(spot, "quantity", 0.0) or 0.0)
        current_price = getattr(spot, "current_price", None)
        total_shares = int(metrics["total_shares"])
        assigned_qty = current_qty + total_shares
        assigned_weight = None
        if current_price and portfolio_total_value > 0 and currency == "USD":
            assigned_weight = round(float(current_price) * assigned_qty / portfolio_total_value * 100, 2)
        reserved = float(getattr(row, "reserved_cash", 0.0) or metrics["reserved_cash"])
        reserved_by_currency[currency] += reserved
        contracts_out.append(
            {
                "id": row.id,
                "underlying_symbol": symbol,
                "expiry_date": str(row.expiry_date),
                "days_to_expiry": (row.expiry_date - date.today()).days,
                "contracts": int(row.contracts),
                "reserved_cash": round(reserved, 2),
                "currency": currency,
                "effective_entry_if_assigned": float(
                    getattr(row, "effective_entry_if_assigned", 0.0)
                    or metrics["effective_entry_if_assigned"]
                ),
                "assigned_total_shares": assigned_qty,
                "assigned_weight_estimate_pct": assigned_weight,
            }
        )

    return {
        "contract_count": len(contracts_out),
        "contracts": contracts_out,
        "reserved_cash_by_currency": dict(reserved_by_currency),
        "cash_by_currency": dict(cash_by_currency),
        "cash_gap_by_currency": {
            currency: round(cash_by_currency.get(currency, 0.0) - reserved, 2)
            for currency, reserved in reserved_by_currency.items()
        },
    }
