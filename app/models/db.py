"""
SQLModel table definitions and DB initialization.
All tables map to domain objects but are separate classes to avoid
coupling persistence concerns with domain logic.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "data" / "investment.db"
DB_URL = f"sqlite:///{DB_PATH}"

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(DB_URL, echo=False)
    return _engine


def init_db():
    """Create all tables if they don't exist, and migrate existing tables."""
    SQLModel.metadata.create_all(get_engine())
    # Add metadata columns to existing positions table if not present
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    existing = {row[1] for row in conn.execute("PRAGMA table_info(positions)")}
    new_cols = [
        ("target_bear", "REAL"), ("target_base", "REAL"), ("target_bull", "REAL"),
        ("prob_bear", "REAL"), ("prob_base", "REAL"), ("prob_bull", "REAL"),
        ("expected_cagr", "REAL"), ("time_horizon_months", "INTEGER"),
        ("sector", "TEXT"), ("region", "TEXT"), ("cap_style", "TEXT"),
        ("growth_value", "TEXT"), ("theme_tags", "TEXT"),
        ("risk_level", "TEXT"), ("ic_status", "TEXT"), ("meta_updated_at", "TIMESTAMP"),
        # Market / currency fields (A-share support)
        ("market", "TEXT"), ("currency", "TEXT"), ("exchange", "TEXT"),
    ]
    for col, col_type in new_cols:
        if col not in existing:
            conn.execute(f"ALTER TABLE positions ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def get_session() -> Session:
    return Session(get_engine())


# ---------------------------------------------------------------------------
# Table models
# ---------------------------------------------------------------------------

class PositionRow(SQLModel, table=True):
    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Scenario targets (written by researcher workflow) ---
    target_bear: Optional[float] = Field(default=None)
    target_base: Optional[float] = Field(default=None)
    target_bull: Optional[float] = Field(default=None)
    prob_bear: Optional[float] = Field(default=None)
    prob_base: Optional[float] = Field(default=None)
    prob_bull: Optional[float] = Field(default=None)
    expected_cagr: Optional[float] = Field(default=None)   # probability-weighted
    time_horizon_months: Optional[int] = Field(default=None)

    # --- Style ---
    sector: Optional[str] = Field(default=None)         # e.g. "Technology"
    region: Optional[str] = Field(default=None)         # "US" / "China" / "Crypto" / "TW"
    cap_style: Optional[str] = Field(default=None)      # "mega" / "large" / "mid" / "small"
    growth_value: Optional[str] = Field(default=None)   # "growth" / "value" / "blend"
    theme_tags: Optional[str] = Field(default=None)     # JSON array e.g. '["AI","semiconductor"]'

    # --- Risk ---
    risk_level: Optional[str] = Field(default=None)     # "low" / "medium" / "high"
    ic_status: Optional[str] = Field(default=None)      # "CLEAR" / "WATCHING" / "TRIGGERED"
    meta_updated_at: Optional[datetime] = Field(default=None)

    # --- Market / currency (A-share support) ---
    market: str = Field(default="US")                   # "US" | "CN_A"
    currency: str = Field(default="USD")                # "USD" | "CNY"
    exchange: Optional[str] = Field(default=None)       # "NASDAQ" | "NYSE" | "SSE" | "SZSE" | "BSE"


class SnapshotRow(SQLModel, table=True):
    __tablename__ = "snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_date: date = Field(index=True)
    total_value: float
    cash: float = 0.0
    daily_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    top_position_weight: float = 0.0
    positions_json: str = "{}"        # serialized list[Position]


class EventRow(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = "news"
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    related_symbols: str = "[]"       # JSON list
    title: str
    summary: str = ""
    importance: float = 0.5
    source: str = ""
    is_noise: Optional[bool] = None


class RecommendationRow(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    scope: str
    action: str
    reason: str
    evidence: str = "[]"              # JSON list
    risk_notes: str = "[]"
    confidence: float = 0.5


class JournalEntryRow(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    scope: str = Field(index=True)
    thesis: str = ""
    user_note: str = ""
    agent_note: str = ""
    linked_rec_ids: str = "[]"        # JSON list
