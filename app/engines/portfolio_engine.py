"""
Portfolio Engine — deterministic calculations on raw position rows.
Supports multi-currency portfolios via FX conversion to base currency (USD).
"""
from __future__ import annotations

from app.models.domain import Position


def compute_positions(rows, fx_rate_cny_usd: float | None = None) -> list[Position]:
    """
    Given DB position rows (with current_price set), compute derived fields.

    For CNY positions, converts to USD using fx_rate_cny_usd.
    If fx_rate_cny_usd is None, it will be fetched from market_data.

    Returns Position objects with local values, FX fields, and USD-based weight.
    """
    # Resolve FX rate
    fx_rate, fx_stale = _resolve_fx_rate(fx_rate_cny_usd)

    # First pass: compute base_market_value for each row (for weight calculation)
    base_values = []
    for r in rows:
        local_mv = r.current_price * r.quantity if r.current_price else 0.0
        currency = getattr(r, "currency", "USD")
        if currency == "CNY":
            base_mv = local_mv * fx_rate if fx_rate else 0.0
        else:
            base_mv = local_mv
        base_values.append(base_mv)

    total_base_value = sum(base_values)

    # Second pass: build Position objects
    positions = []
    for r, base_mv in zip(rows, base_values):
        local_price = r.current_price or 0.0
        local_mv = local_price * r.quantity

        # Cost basis is in local currency (avg_cost is stored in local currency)
        cost = r.avg_cost * r.quantity
        pnl = local_mv - cost
        pnl_pct = (pnl / cost * 100) if cost else 0.0

        weight = (base_mv / total_base_value * 100) if total_base_value else 0.0

        currency = getattr(r, "currency", None) or "USD"
        market = getattr(r, "market", None) or "US"

        if currency == "CNY":
            fx_to_base = fx_rate or 0.0
            price_source = "jqdata"
        else:
            fx_to_base = 1.0
            price_source = "yfinance"

        positions.append(Position(
            symbol=r.symbol,
            quantity=r.quantity,
            avg_cost=r.avg_cost,
            current_price=local_price,
            market_value=local_mv,
            unrealized_pnl=pnl,
            unrealized_pnl_pct=pnl_pct,
            weight=weight,
            market=market,
            currency=currency,
            local_price=local_price,
            local_market_value=local_mv,
            fx_rate_to_base=fx_to_base,
            base_market_value=base_mv,
            fx_stale=fx_stale if currency == "CNY" else False,
            price_source=price_source,
        ))

    return positions


def _resolve_fx_rate(provided: float | None) -> tuple[float | None, bool]:
    """
    Returns (fx_rate, is_stale).
    Uses provided rate if given; otherwise fetches from market_data.
    """
    if provided is not None:
        return provided, False
    try:
        from app.services.market_data import get_fx_rate
        rate = get_fx_rate("CNY", "USD")
        return rate, False
    except Exception:
        return None, True
