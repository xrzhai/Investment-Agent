"""
Domain models — pure Pydantic, no DB coupling.
These are the internal data structures used across all layers.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"
    cash = "cash"
    other = "other"


class ActionType(str, Enum):
    hold = "hold"
    monitor = "monitor"
    research = "research"
    consider_trim = "consider_trim"
    consider_rebalance = "consider_rebalance"
    no_action = "no_action"


class TriggerType(str, Enum):
    concentration = "concentration"
    drawdown = "drawdown"
    forbidden_asset = "forbidden_asset"
    price_move = "price_move"
    event = "event"
    thesis_drift = "thesis_drift"


# ---------------------------------------------------------------------------
# Core domain objects
# ---------------------------------------------------------------------------

class Asset(BaseModel):
    symbol: str
    name: str = ""
    asset_type: AssetType = AssetType.stock
    sector: str = ""
    market: str = "US"


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float                    # per share cost basis, in local currency
    current_price: float = 0.0        # local currency price
    market_value: float = 0.0         # local currency market value
    unrealized_pnl: float = 0.0       # local currency PnL
    unrealized_pnl_pct: float = 0.0
    weight: float = 0.0               # % of total portfolio (based on base_market_value)

    # Market / currency
    market: str = "US"                # "US" | "CN_A"
    currency: str = "USD"             # "USD" | "CNY"

    # FX / base currency fields (populated after FX conversion)
    local_price: float = 0.0          # same as current_price (explicit alias)
    local_market_value: float = 0.0   # same as market_value (explicit alias)
    fx_rate_to_base: float = 1.0      # e.g. 0.1377 for CNY→USD
    base_market_value: float = 0.0    # market_value converted to base currency (USD)
    fx_stale: bool = False            # True if FX rate is from a prior day
    price_source: str = "yfinance"    # "yfinance" | "jqdata" | "cached"


class PortfolioSnapshot(BaseModel):
    snapshot_date: date
    total_value: float
    cash: float = 0.0
    positions: list[Position] = Field(default_factory=list)
    daily_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0      # from peak within tracked history
    top_position_weight: float = 0.0   # largest single position weight


class InvestorProfile(BaseModel):
    style: str = "growth"              # e.g. growth, value, blend
    time_horizon: str = "long"         # short / medium / long
    risk_tolerance: str = "medium"     # low / medium / high
    max_position_weight: float = 0.20  # e.g. 0.20 = 20%
    max_drawdown_tolerance: float = 0.15
    min_cash_pct: float = 0.05
    forbidden_symbols: list[str] = Field(default_factory=list)
    notes: str = ""


class PolicyTrigger(BaseModel):
    trigger_type: TriggerType
    symbol: Optional[str] = None       # None = portfolio-level
    current_value: float
    threshold: float
    message: str


class PolicyResult(BaseModel):
    has_violations: bool
    triggers: list[PolicyTrigger] = Field(default_factory=list)


class Event(BaseModel):
    event_id: Optional[int] = None
    event_type: str = "news"
    timestamp: datetime = Field(default_factory=datetime.now)
    related_symbols: list[str] = Field(default_factory=list)
    title: str
    summary: str = ""
    importance: float = 0.5            # 0–1
    source: str = ""
    is_noise: Optional[bool] = None


class RecommendationDraft(BaseModel):
    """Structured intermediate before LLM verbalization."""
    scope: str                         # "portfolio" or ticker symbol
    trigger_type: TriggerType
    suggested_action: ActionType
    rationale_points: list[str] = Field(default_factory=list)
    evidence_points: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    confidence: float = 0.5            # 0–1


class Recommendation(BaseModel):
    rec_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    scope: str
    action: ActionType
    reason: str
    evidence: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class JournalEntry(BaseModel):
    entry_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    scope: str                         # ticker or "portfolio"
    thesis: str = ""
    user_note: str = ""
    agent_note: str = ""
    linked_rec_ids: list[int] = Field(default_factory=list)
