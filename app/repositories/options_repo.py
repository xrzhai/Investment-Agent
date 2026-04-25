"""Repository and summary helpers for sold put contracts."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Iterable, Optional

from sqlmodel import select

from app.models.db import OptionContractRow, get_session, init_db
from app.repositories.portfolio_repo import get_position, upsert_position
from app.services.market_data import get_batch_prices, get_fx_rate


def _normalize_contracts(contracts: int) -> int:
    n = abs(int(contracts))
    if n <= 0:
        raise ValueError("contracts must be non-zero")
    return n


def derive_open_put_metrics(
    *,
    strike: float,
    contracts: int,
    premium_per_share: float,
    shares_per_contract: int = 100,
    fees: float = 0.0,
) -> dict:
    if strike <= 0:
        raise ValueError("strike must be positive")
    if shares_per_contract <= 0:
        raise ValueError("shares_per_contract must be positive")
    if premium_per_share < 0:
        raise ValueError("premium_per_share cannot be negative")
    if fees < 0:
        raise ValueError("fees cannot be negative")

    contract_count = _normalize_contracts(contracts)
    total_shares = contract_count * shares_per_contract
    premium_total = round(total_shares * premium_per_share, 2)
    reserved_cash = round(total_shares * strike, 2)
    net_cash_obligation = round(reserved_cash - premium_total + fees, 2)
    effective_entry_if_assigned = round(net_cash_obligation / total_shares, 2)
    return {
        "contract_count": contract_count,
        "total_shares": total_shares,
        "premium_total": premium_total,
        "reserved_cash": reserved_cash,
        "net_cash_obligation": net_cash_obligation,
        "effective_entry_if_assigned": effective_entry_if_assigned,
    }


def _validate_new_contract_dates(opened_date: date | None, expiry_date: date) -> None:
    if opened_date and opened_date > expiry_date:
        raise ValueError("opened_date cannot be after expiry_date")


def _require_open_status(row: OptionContractRow, action: str) -> None:
    if row.status != "open":
        raise ValueError(f"Cannot {action} option contract #{row.id}: current status is {row.status}, expected open.")


def _preferred_metric(row_value, derived_value):
    if row_value is None:
        return derived_value
    try:
        numeric = float(row_value)
    except (TypeError, ValueError):
        return row_value
    if numeric <= 0:
        return derived_value
    return row_value


def _currency_to_cash_symbol(currency: str) -> str:
    return "CASH_CNY" if currency.upper() == "CNY" else "CASH_USD"


def _apply_assignment_to_portfolio(row: OptionContractRow) -> None:
    total_shares = int(row.contracts) * int(row.shares_per_contract)
    net_cash_obligation = float(_preferred_metric(row.net_cash_obligation, 0.0))
    current_position = get_position(row.underlying_symbol)
    if current_position:
        new_qty = float(current_position.quantity) + total_shares
        new_avg_cost = ((float(current_position.quantity) * float(current_position.avg_cost)) + net_cash_obligation) / new_qty
    else:
        new_qty = float(total_shares)
        new_avg_cost = net_cash_obligation / total_shares
    upsert_position(
        row.underlying_symbol,
        new_qty,
        new_avg_cost,
        market=row.market,
        currency=row.currency,
    )

    cash_symbol = _currency_to_cash_symbol(row.currency)
    current_cash = get_position(cash_symbol)
    current_cash_qty = float(current_cash.quantity) if current_cash else 0.0
    cash_after = current_cash_qty - net_cash_obligation
    cash_cost = float(current_cash.avg_cost) if current_cash and current_cash.avg_cost else (
        get_fx_rate("CNY", "USD") if cash_symbol == "CASH_CNY" else 1.0
    )
    upsert_position(
        cash_symbol,
        cash_after,
        cash_cost,
        market="US",
        currency="USD",
    )


def create_option_contract(
    *,
    underlying_symbol: str,
    expiry_date: date,
    strike: float,
    contracts: int,
    premium_per_share: float,
    shares_per_contract: int = 100,
    opened_date: date | None = None,
    fees: float = 0.0,
    currency: str = "USD",
    market: str = "US",
    intent: str = "lower_price_entry",
    notes: str = "",
    linked_decision_file: str = "",
) -> OptionContractRow:
    init_db()
    _validate_new_contract_dates(opened_date, expiry_date)
    metrics = derive_open_put_metrics(
        strike=strike,
        contracts=contracts,
        premium_per_share=premium_per_share,
        shares_per_contract=shares_per_contract,
        fees=fees,
    )
    with get_session() as session:
        row = OptionContractRow(
            underlying_symbol=underlying_symbol.upper(),
            option_type="put",
            side="short",
            contracts=metrics["contract_count"],
            shares_per_contract=shares_per_contract,
            strike=strike,
            expiry_date=expiry_date,
            opened_date=opened_date,
            premium_per_share=premium_per_share,
            premium_total=metrics["premium_total"],
            fees=fees,
            currency=currency.upper(),
            market=market.upper(),
            status="open",
            reserved_cash=metrics["reserved_cash"],
            net_cash_obligation=metrics["net_cash_obligation"],
            effective_entry_if_assigned=metrics["effective_entry_if_assigned"],
            intent=intent,
            notes=notes,
            linked_decision_file=linked_decision_file,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_option_contracts(status: str | None = None) -> list[OptionContractRow]:
    init_db()
    with get_session() as session:
        stmt = select(OptionContractRow)
        if status:
            stmt = stmt.where(OptionContractRow.status == status)
        stmt = stmt.order_by(OptionContractRow.expiry_date.asc(), OptionContractRow.underlying_symbol.asc())
        return list(session.exec(stmt).all())


def get_option_contract(contract_id: int) -> Optional[OptionContractRow]:
    init_db()
    with get_session() as session:
        return session.get(OptionContractRow, contract_id)


def mark_option_assigned(
    contract_id: int,
    *,
    assigned_date: date | None = None,
    assignment_price: float | None = None,
    notes: str = "",
    apply_to_spot: bool = False,
) -> OptionContractRow:
    init_db()
    with get_session() as session:
        row = session.get(OptionContractRow, contract_id)
        if not row:
            raise ValueError(f"option contract #{contract_id} not found")
        _require_open_status(row, "assign")
        event_date = assigned_date or date.today()
        if row.opened_date and event_date < row.opened_date:
            raise ValueError("assigned_date cannot be before opened_date")
        if assignment_price is not None and assignment_price <= 0:
            raise ValueError("assignment_price must be positive")
        row.status = "assigned"
        row.assigned_date = event_date
        row.assignment_price = assignment_price if assignment_price is not None else row.strike
        row.realized_premium = round(row.premium_total - row.fees, 2)
        if notes:
            row.notes = _merge_notes(row.notes, notes)
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        session.refresh(row)
    if apply_to_spot:
        _apply_assignment_to_portfolio(row)
    return row


def mark_option_expired(contract_id: int, *, expired_date: date | None = None, notes: str = "") -> OptionContractRow:
    init_db()
    with get_session() as session:
        row = session.get(OptionContractRow, contract_id)
        if not row:
            raise ValueError(f"option contract #{contract_id} not found")
        _require_open_status(row, "expire")
        event_date = expired_date or date.today()
        if row.opened_date and event_date < row.opened_date:
            raise ValueError("expired_date cannot be before opened_date")
        if event_date < row.expiry_date:
            raise ValueError("expired_date cannot be before contract expiry_date")
        row.status = "expired"
        row.closed_date = event_date
        row.realized_premium = round(row.premium_total - row.fees, 2)
        if notes:
            row.notes = _merge_notes(row.notes, notes)
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def mark_option_closed(
    contract_id: int,
    *,
    closed_date: date | None = None,
    realized_cost_to_close: float = 0.0,
    notes: str = "",
) -> OptionContractRow:
    if realized_cost_to_close < 0:
        raise ValueError("realized_cost_to_close cannot be negative")
    init_db()
    with get_session() as session:
        row = session.get(OptionContractRow, contract_id)
        if not row:
            raise ValueError(f"option contract #{contract_id} not found")
        _require_open_status(row, "close")
        event_date = closed_date or date.today()
        if row.opened_date and event_date < row.opened_date:
            raise ValueError("closed_date cannot be before opened_date")
        if event_date > row.expiry_date:
            raise ValueError("closed_date cannot be after contract expiry_date; use expire instead")
        row.status = "closed"
        row.closed_date = event_date
        row.realized_premium = round(row.premium_total - realized_cost_to_close - row.fees, 2)
        if notes:
            row.notes = _merge_notes(row.notes, notes)
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def compute_open_put_exposure(
    *,
    spot_positions: Iterable,
    option_rows: Iterable,
    total_portfolio_value_usd: float | None = None,
    fetch_spot_prices: bool = False,
) -> dict:
    spot_positions = list(spot_positions)
    option_rows = [r for r in option_rows if getattr(r, "status", "open") == "open"]
    if total_portfolio_value_usd is None:
        total_portfolio_value_usd = round(sum(float(getattr(p, "base_market_value", 0.0) or 0.0) for p in spot_positions), 2)

    spot_by_symbol = {str(getattr(p, "symbol", "")).upper(): p for p in spot_positions}
    cash_by_currency: dict[str, float] = defaultdict(float)
    for p in spot_positions:
        symbol = str(getattr(p, "symbol", "")).upper()
        if symbol.startswith("CASH_"):
            if symbol == "CASH_CNY":
                currency = "CNY"
            elif symbol == "CASH_USD":
                currency = "USD"
            else:
                currency = str(getattr(p, "currency", "USD") or "USD").upper()
            cash_by_currency[currency] += round(float(getattr(p, "quantity", 0.0) or 0.0), 2)

    missing_symbols = [
        r.underlying_symbol.upper()
        for r in option_rows
        if getattr(spot_by_symbol.get(r.underlying_symbol.upper()), "current_price", 0.0) in (None, 0, 0.0)
    ]
    price_lookup: dict[str, float | None] = {}
    if fetch_spot_prices and missing_symbols:
        price_lookup = get_batch_prices(sorted(set(missing_symbols)))

    reserved_cash_by_currency: dict[str, float] = defaultdict(float)
    premium_total_by_currency: dict[str, float] = defaultdict(float)
    contracts_out = []

    for row in option_rows:
        symbol = row.underlying_symbol.upper()
        currency = str(getattr(row, "currency", "USD") or "USD").upper()
        current_spot = spot_by_symbol.get(symbol)
        current_qty = float(getattr(current_spot, "quantity", 0.0) or 0.0)
        current_avg_cost = getattr(current_spot, "avg_cost", None)
        spot_price = getattr(current_spot, "current_price", None)
        if spot_price in (None, 0, 0.0):
            spot_price = price_lookup.get(symbol)
        if spot_price is not None:
            spot_price = round(float(spot_price), 4)

        total_shares = int(row.contracts) * int(row.shares_per_contract)
        derived_metrics = derive_open_put_metrics(
            strike=float(row.strike),
            contracts=int(row.contracts),
            premium_per_share=float(getattr(row, "premium_per_share", 0.0) or 0.0),
            shares_per_contract=int(row.shares_per_contract),
            fees=float(getattr(row, "fees", 0.0) or 0.0),
        )
        net_cash_obligation = float(_preferred_metric(getattr(row, "net_cash_obligation", None), derived_metrics["net_cash_obligation"]))
        reserved_cash = float(_preferred_metric(getattr(row, "reserved_cash", None), derived_metrics["reserved_cash"]))
        premium_total = float(_preferred_metric(getattr(row, "premium_total", None), derived_metrics["premium_total"]))
        effective_entry_if_assigned = float(
            _preferred_metric(getattr(row, "effective_entry_if_assigned", None), derived_metrics["effective_entry_if_assigned"])
        )
        assigned_total_shares = current_qty + total_shares
        assigned_avg_cost = None
        if assigned_total_shares > 0 and current_avg_cost is not None:
            assigned_avg_cost = round(
                ((current_qty * float(current_avg_cost)) + net_cash_obligation) / assigned_total_shares,
                4,
            )
        elif assigned_total_shares > 0:
            assigned_avg_cost = round(net_cash_obligation / assigned_total_shares, 4)

        days_to_expiry = (row.expiry_date - date.today()).days
        strike_gap = None
        moneyness = "unknown"
        if spot_price is not None:
            strike_gap = round(float(spot_price) - float(row.strike), 2)
            if abs(strike_gap) / float(row.strike) <= 0.02:
                moneyness = "atm"
            elif float(spot_price) < float(row.strike):
                moneyness = "itm"
            else:
                moneyness = "otm"

        assigned_weight_estimate = None
        if spot_price is not None and total_portfolio_value_usd:
            assigned_value = float(spot_price) * assigned_total_shares
            assigned_weight_estimate = round(assigned_value / total_portfolio_value_usd * 100, 2)

        reserved_cash_by_currency[currency] += round(reserved_cash, 2)
        premium_total_by_currency[currency] += round(premium_total, 2)
        contracts_out.append(
            {
                "id": row.id,
                "underlying_symbol": symbol,
                "contracts": int(row.contracts),
                "shares_per_contract": int(row.shares_per_contract),
                "strike": round(float(row.strike), 4),
                "expiry_date": str(row.expiry_date),
                "premium_per_share": round(float(row.premium_per_share), 4),
                "premium_total": round(premium_total, 2),
                "fees": round(float(row.fees), 2),
                "reserved_cash": round(reserved_cash, 2),
                "net_cash_obligation": round(net_cash_obligation, 2),
                "effective_entry_if_assigned": round(effective_entry_if_assigned, 4),
                "current_spot_qty": round(current_qty, 4),
                "current_spot_avg_cost": None if current_avg_cost is None else round(float(current_avg_cost), 4),
                "assigned_total_shares": round(float(assigned_total_shares), 4),
                "assigned_avg_cost": assigned_avg_cost,
                "spot_price": spot_price,
                "strike_gap": strike_gap,
                "moneyness": moneyness,
                "days_to_expiry": days_to_expiry,
                "assigned_weight_estimate_pct": assigned_weight_estimate,
                "status": row.status,
                "intent": row.intent,
                "notes": row.notes,
            }
        )

    cash_gap_vs_reserved_by_currency = {
        currency: round(cash_by_currency.get(currency, 0.0) - reserved, 2)
        for currency, reserved in reserved_cash_by_currency.items()
    }

    return {
        "contract_count": len(contracts_out),
        "contracts": contracts_out,
        "totals": {
            "reserved_cash_by_currency": dict(sorted(reserved_cash_by_currency.items())),
            "premium_total_by_currency": dict(sorted(premium_total_by_currency.items())),
            "cash_by_currency": dict(sorted((k, round(v, 2)) for k, v in cash_by_currency.items())),
            "cash_gap_vs_reserved_by_currency": dict(sorted(cash_gap_vs_reserved_by_currency.items())),
            "portfolio_total_value_usd": round(float(total_portfolio_value_usd or 0.0), 2),
        },
    }


def _merge_notes(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    new = (new or "").strip()
    if not existing:
        return new
    if not new:
        return existing
    return f"{existing}\n{new}"
