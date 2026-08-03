from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PositionRecord(BaseModel):
    id: int | None = None
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    market: str = "US"
    currency: str = "USD"
    exchange: str | None = None
    sector: str | None = None
    region: str | None = None
    cap_style: str | None = None
    growth_value: str | None = None
    theme_tags: list[str] = Field(default_factory=list)
    risk_level: str | None = None
    updated_at: datetime | None = None

    @field_validator("theme_tags", mode="before")
    @classmethod
    def parse_theme_tags(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class InstrumentMetadata(BaseModel):
    symbol: str
    sector: str | None = None
    region: str | None = None
    cap_style: str | None = None
    growth_value: str | None = None
    theme_tags: list[str] = Field(default_factory=list)
    risk_level: str | None = None
    source: str
    source_ref: str | None = None
    updated_at: datetime

    @field_validator("theme_tags", mode="before")
    @classmethod
    def parse_theme_tags(cls, value):
        return PositionRecord.parse_theme_tags(value)


class QuoteRecord(BaseModel):
    id: int | None = None
    symbol: str
    price: float
    currency: str
    as_of: datetime
    source: str
    source_ref: str | None = None
    recorded_at: datetime


class PositionView(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    currency: str
    market: str
    sector: str | None = None
    region: str | None = None
    cap_style: str | None = None
    growth_value: str | None = None
    theme_tags: list[str] = Field(default_factory=list)
    risk_level: str | None = None
    current_price: float | None = None
    quote_as_of: datetime | None = None
    quote_source: str | None = None
    local_market_value: float | None = None
    base_market_value: float | None = None
    unrealized_pnl_local: float | None = None
    unrealized_pnl_pct: float | None = None
    fx_rate_to_base: float | None = None
    fx_as_of: datetime | None = None
    fx_source: str | None = None
    weight_pct: float | None = None
    data_quality: list[str] = Field(default_factory=list)


class OptionContractRecord(BaseModel):
    id: int | None = None
    underlying_symbol: str
    option_type: str = "put"
    side: str = "short"
    contracts: int = 1
    shares_per_contract: int = 100
    strike: float
    expiry_date: date
    opened_date: date | None = None
    premium_per_share: float = 0.0
    premium_total: float = 0.0
    fees: float = 0.0
    currency: str = "USD"
    market: str = "US"
    status: str = "open"
    reserved_cash: float = 0.0
    net_cash_obligation: float = 0.0
    effective_entry_if_assigned: float = 0.0
    intent: str = "lower_price_entry"
    notes: str = ""
    linked_decision_file: str = ""
    closed_date: date | None = None
    assigned_date: date | None = None
    assignment_price: float | None = None
    realized_premium: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PortfolioEvent(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    symbol: str | None = None
    payload: dict[str, Any]
    source: str
    source_ref: str | None = None
    recorded_at: datetime


class PortfolioState(BaseModel):
    as_of: datetime
    base_currency: str = "USD"
    total_value: float
    total_cost: float | None = None
    total_unrealized_pnl: float | None = None
    cash_value: float
    cash_pct: float | None = None
    valuation_complete: bool = True
    held_position_count: int = 0
    priced_position_count: int = 0
    sector_exposure_pct: dict[str, float] = Field(default_factory=dict)
    region_exposure_pct: dict[str, float] = Field(default_factory=dict)
    theme_exposure_pct: dict[str, float] = Field(default_factory=dict)
    positions: list[PositionView]
    open_options: list[OptionContractRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InvestorProfile(BaseModel):
    style: str = "growth"
    time_horizon: str = "long"
    risk_tolerance: str = "medium"
    max_position_weight: float = 0.20
    max_drawdown_tolerance: float = 0.15
    min_cash_pct: float = 0.05
    forbidden_symbols: list[str] = Field(default_factory=list)
    notes: str = ""


class PolicySignal(BaseModel):
    signal_type: str
    severity: str
    symbol: str | None = None
    current_value: float | None = None
    threshold: float | None = None
    message: str


class PolicyReport(BaseModel):
    as_of: datetime
    signals: list[PolicySignal]
    warnings: list[str] = Field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return any(signal.severity == "violation" for signal in self.signals)


class TradeResult(BaseModel):
    event_id: str
    symbol: str
    side: str
    trade_quantity: float
    trade_price: float
    fees: float
    previous_quantity: float
    new_quantity: float
    new_avg_cost: float | None
    closed: bool


class SnapshotRecord(BaseModel):
    id: int | None = None
    snapshot_date: date
    total_value: float
    cash: float = 0.0
    daily_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    top_position_weight: float = 0.0
    positions_json: str = "{}"
    notes: str | None = None


class CashflowRecord(BaseModel):
    id: int | None = None
    event_date: date
    amount_usd: float
    description: str = ""
    created_at: datetime | None = None
