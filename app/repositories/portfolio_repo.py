"""
Portfolio repository — CRUD for positions and snapshots.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.db import PositionRow, SnapshotRow, get_session
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
