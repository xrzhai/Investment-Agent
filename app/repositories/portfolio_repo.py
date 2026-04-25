"""
Portfolio repository — CRUD for positions and snapshots.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.db import CashflowEventRow, PositionRow, SnapshotRow, get_session
from app.models.domain import Position, PortfolioSnapshot


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def upsert_position(
    symbol: str,
    quantity: float,
    avg_cost: float,
    market: str = "US",
    currency: str | None = None,
    exchange: str | None = None,
) -> PositionRow:
    """
    Insert or update a position.
    currency defaults to "CNY" for CN_A and "USD" for US if not specified.
    """
    if currency is None:
        currency = "CNY" if market == "CN_A" else "USD"
    with get_session() as session:
        row = session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()
        if row:
            row.quantity = quantity
            row.avg_cost = avg_cost
            row.market = market
            row.currency = currency
            if exchange is not None:
                row.exchange = exchange
            row.updated_at = datetime.now()
        else:
            row = PositionRow(
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
                market=market,
                currency=currency,
                exchange=exchange,
            )
            session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_position(symbol: str) -> Optional[PositionRow]:
    with get_session() as session:
        return session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()


def apply_trade(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    fees: float = 0.0,
    market: str = "US",
    currency: str | None = None,
    exchange: str | None = None,
) -> tuple[Optional[PositionRow], dict]:
    """
    Apply an incremental trade to an existing position.

    BUY:
      - increases quantity
      - recalculates weighted average cost, including fees

    SELL:
      - decreases quantity
      - keeps average cost unchanged for the remaining position
      - deletes the row if fully exited
    """
    side = side.lower()
    if side not in {"buy", "sell"}:
        raise ValueError(f"Unsupported trade side: {side}")
    if quantity <= 0:
        raise ValueError("Trade quantity must be positive.")
    if price <= 0:
        raise ValueError("Trade price must be positive.")
    if fees < 0:
        raise ValueError("Fees cannot be negative.")

    if currency is None:
        currency = "CNY" if market == "CN_A" else "USD"

    with get_session() as session:
        row = session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()

        if side == "buy":
            trade_total = quantity * price + fees
            if row:
                old_total_cost = row.quantity * row.avg_cost
                new_quantity = row.quantity + quantity
                row.avg_cost = (old_total_cost + trade_total) / new_quantity
                row.quantity = new_quantity
                row.market = market
                row.currency = currency
                if exchange is not None:
                    row.exchange = exchange
                row.updated_at = datetime.now()
            else:
                row = PositionRow(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=trade_total / quantity,
                    market=market,
                    currency=currency,
                    exchange=exchange,
                )
                session.add(row)
            session.commit()
            session.refresh(row)
            return row, {
                "side": side,
                "trade_qty": quantity,
                "trade_price": price,
                "fees": fees,
                "new_qty": row.quantity,
                "new_avg_cost": row.avg_cost,
                "closed": False,
            }

        if not row:
            raise ValueError(f"Cannot sell {symbol}: no existing position found.")
        if quantity > row.quantity:
            raise ValueError(
                f"Cannot sell {quantity} shares of {symbol}: only {row.quantity} available."
            )

        remaining_qty = row.quantity - quantity
        avg_cost = row.avg_cost
        closed = remaining_qty == 0
        if closed:
            session.delete(row)
            session.commit()
            return None, {
                "side": side,
                "trade_qty": quantity,
                "trade_price": price,
                "fees": fees,
                "new_qty": 0.0,
                "new_avg_cost": avg_cost,
                "closed": True,
            }

        row.quantity = remaining_qty
        row.market = market
        row.currency = currency
        if exchange is not None:
            row.exchange = exchange
        row.updated_at = datetime.now()
        session.commit()
        session.refresh(row)
        return row, {
            "side": side,
            "trade_qty": quantity,
            "trade_price": price,
            "fees": fees,
            "new_qty": row.quantity,
            "new_avg_cost": row.avg_cost,
            "closed": False,
        }


def update_price(symbol: str, price: float) -> Optional[PositionRow]:
    with get_session() as session:
        row = session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()
        if row:
            row.current_price = price
            row.updated_at = datetime.now()
            session.commit()
            session.refresh(row)
        return row


def list_positions() -> list[PositionRow]:
    with get_session() as session:
        return session.exec(select(PositionRow)).all()


def update_position_meta(symbol: str, meta: dict) -> Optional[PositionRow]:
    """Write extracted metadata fields to an existing position row."""
    with get_session() as session:
        row = session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()
        if not row:
            return None
        for key, value in meta.items():
            if hasattr(row, key):
                setattr(row, key, value)
        row.meta_updated_at = datetime.now()
        session.commit()
        session.refresh(row)
        return row


def delete_position(symbol: str) -> bool:
    with get_session() as session:
        row = session.exec(select(PositionRow).where(PositionRow.symbol == symbol)).first()
        if row:
            session.delete(row)
            session.commit()
            return True
        return False


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def save_snapshot(snap: PortfolioSnapshot) -> SnapshotRow:
    from app.models.domain import Position
    with get_session() as session:
        positions_json = json.dumps([p.model_dump() for p in snap.positions], default=str)
        row = SnapshotRow(
            snapshot_date=snap.snapshot_date,
            total_value=snap.total_value,
            cash=snap.cash,
            daily_return_pct=snap.daily_return_pct,
            max_drawdown_pct=snap.max_drawdown_pct,
            top_position_weight=snap.top_position_weight,
            positions_json=positions_json,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_snapshot(snap_date: date) -> Optional[SnapshotRow]:
    with get_session() as session:
        return session.exec(
            select(SnapshotRow).where(SnapshotRow.snapshot_date == snap_date)
        ).first()


def list_snapshots(limit: int = 30) -> list[SnapshotRow]:
    with get_session() as session:
        return session.exec(
            select(SnapshotRow).order_by(SnapshotRow.snapshot_date.desc()).limit(limit)
        ).all()


def list_snapshots_asc() -> list[SnapshotRow]:
    """Return all snapshots ordered by date ascending (for TWR calculation)."""
    with get_session() as session:
        return session.exec(
            select(SnapshotRow).order_by(SnapshotRow.snapshot_date.asc())
        ).all()


def upsert_pnl_snapshot(total_value_usd: float, notes: str = "") -> SnapshotRow:
    """
    Insert or update today's snapshot for P&L curve tracking.
    If a row for today already exists, update its total_value and notes.
    """
    today = date.today()
    with get_session() as session:
        row = session.exec(
            select(SnapshotRow).where(SnapshotRow.snapshot_date == today)
        ).first()
        if row:
            row.total_value = total_value_usd
            row.notes = notes
        else:
            row = SnapshotRow(
                snapshot_date=today,
                total_value=total_value_usd,
                notes=notes,
            )
            session.add(row)
        session.commit()
        session.refresh(row)
        return row


# ---------------------------------------------------------------------------
# Cashflow events
# ---------------------------------------------------------------------------

def save_cashflow(event_date: date, amount_usd: float, description: str = "") -> CashflowEventRow:
    """Record a deposit (positive) or withdrawal (negative) event."""
    with get_session() as session:
        row = CashflowEventRow(
            event_date=event_date,
            amount_usd=amount_usd,
            description=description,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_cashflows() -> list[CashflowEventRow]:
    """Return all cashflow events ordered by date ascending."""
    with get_session() as session:
        return session.exec(
            select(CashflowEventRow).order_by(CashflowEventRow.event_date.asc())
        ).all()
