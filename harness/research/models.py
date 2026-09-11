from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ResearchState(str, Enum):
    active = "active"
    watch = "watch"
    paused = "paused"
    closed = "closed"


class FactType(str, Enum):
    reported = "reported"
    guidance = "guidance"
    consensus = "consensus"
    assumption = "assumption"
    inference = "inference"


class FactStatus(str, Enum):
    active = "active"
    superseded = "superseded"
    disputed = "disputed"
    unverified = "unverified"


class SourceType(str, Enum):
    filing = "filing"
    earnings_release = "earnings_release"
    presentation = "presentation"
    transcript = "transcript"
    official_data = "official_data"
    market_data = "market_data"
    news = "news"
    research = "research"
    web = "web"
    other = "other"


class SourceRecord(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_type: SourceType
    publisher: str = Field(min_length=1)
    published_at: datetime | date | None = None
    published_at_unknown_reason: str = ""
    retrieved_at: datetime | None = None
    primary: bool = False
    url: str | None = None
    local_path: str | None = None
    sha256: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def require_location(self) -> "SourceRecord":
        if not self.url and not self.local_path:
            raise ValueError("source requires url or local_path")
        if self.published_at is None and not self.published_at_unknown_reason.strip():
            raise ValueError("source requires published_at or published_at_unknown_reason")
        return self


class FactRecord(BaseModel):
    fact_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    fact_key: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    fact_type: FactType
    value: str | int | float | bool | None = None
    unit: str = ""
    period: str | None = None
    as_of: date | datetime | None = None
    available_at: date | datetime | None = None
    source_ids: list[str] = Field(min_length=1)
    locator: str = ""
    status: FactStatus = FactStatus.active
    supersedes: str | None = None
    tags: list[str] = Field(default_factory=list)
    recorded_at: datetime

    @model_validator(mode="after")
    def validate_time_and_supersession(self) -> "FactRecord":
        if self.fact_type in {FactType.reported, FactType.guidance, FactType.consensus}:
            if self.as_of is None and not self.period:
                raise ValueError(f"{self.fact_type.value} fact requires as_of or period")
        if self.supersedes == self.fact_id:
            raise ValueError("fact cannot supersede itself")
        return self


class ResearchStatus(BaseModel):
    schema_version: str = "1"
    symbol: str
    company_name: str = ""
    research_state: ResearchState = ResearchState.active
    coverage_stage: str = "building"
    current_thesis: str | None = None
    thesis_as_of: date | None = None
    valuation_status: str = "missing"
    valuation_as_of: date | None = None
    summary_path: str = "summary.md"
    facts_path: str = "facts.jsonl"
    sources_path: str = "sources.json"
    last_event_at: datetime | date | None = None
    last_reviewed_at: datetime | date | None = None
    next_review_trigger: str = ""
    active_topics: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    legacy_layout: bool = False


class ResearchBundle(BaseModel):
    status: ResearchStatus
    summary: str = ""
    current_thesis: str | None = None
    facts: list[FactRecord] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
