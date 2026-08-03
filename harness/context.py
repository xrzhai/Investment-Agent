from __future__ import annotations

import json
import re
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from harness.models import LoadedDocument
from harness.research.models import FactRecord, ResearchStatus, SourceRecord
from harness.research.store import ResearchStore

if TYPE_CHECKING:
    from harness.portfolio.service import PortfolioService


class ContextTask(str, Enum):
    research_scan = "research_scan"
    event_intake = "event_intake"
    research_update = "research_update"
    thesis_review = "thesis_review"
    portfolio_review = "portfolio_review"
    decision = "decision"
    trade_record = "trade_record"
    postmortem = "postmortem"


_SYMBOL_TASKS = {
    ContextTask.research_scan,
    ContextTask.event_intake,
    ContextTask.research_update,
    ContextTask.thesis_review,
    ContextTask.decision,
}

_FULL_THESIS_TASKS = {
    ContextTask.research_update,
    ContextTask.thesis_review,
    ContextTask.decision,
}

_PORTFOLIO_TASKS = {
    ContextTask.portfolio_review,
    ContextTask.decision,
    ContextTask.trade_record,
}


class ContextRequest(BaseModel):
    task: ContextTask
    symbol: str | None = None
    topics: list[str] = Field(default_factory=list)
    as_of: date | None = None
    max_chars: int = Field(default=40_000, ge=5_000, le=200_000)
    max_facts: int = Field(default=60, ge=1, le=500)
    portfolio_events_after: datetime | None = None
    max_portfolio_events: int = Field(default=50, ge=1, le=200)
    decision_ref: str | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class ContextPlan(BaseModel):
    task: ContextTask
    symbol: str | None = None
    include: list[str]
    exclude: list[str]
    reason: str


class ResearchOverview(BaseModel):
    symbol: str
    status: ResearchStatus
    summary: str


class ContextPack(BaseModel):
    task: ContextTask
    symbol: str | None = None
    research_status: ResearchStatus | None = None
    documents: list[LoadedDocument] = Field(default_factory=list)
    facts: list[FactRecord] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    research_overview: list[ResearchOverview] = Field(default_factory=list)
    portfolio_state: dict[str, Any] | None = None
    portfolio_events: list[dict[str, Any]] = Field(default_factory=list)
    loaded_paths: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    total_chars: int = 0


class ContextRouter:
    """Build bounded task context and make exclusions explicit."""

    def __init__(
        self,
        research: ResearchStore | None = None,
        portfolio: "PortfolioService | None" = None,
    ):
        self.research = research or ResearchStore()
        self.portfolio = portfolio

    def plan(self, request: ContextRequest) -> ContextPlan:
        if request.task in _SYMBOL_TASKS and not request.symbol:
            raise ValueError(f"{request.task.value} requires a symbol")
        if request.task == ContextTask.trade_record and not request.decision_ref:
            raise ValueError("trade_record requires decision_ref")

        include = ["AGENTS.md", "contracts/context-policy.md", f"workflows/{request.task.value.replace('_', '-')}.md"]
        exclude = [
            "coverage/*/archive/**",
            "old thesis versions",
            "coverage/*/source_docs/** except targeted excerpts",
            "research_notes/**",
            "historical reviews",
            "unrelated symbols",
        ]

        if request.task in _SYMBOL_TASKS:
            include.extend(["symbol status", "bounded summary", "task-relevant active facts", "metadata for sources actually referenced"])
        if request.task in _FULL_THESIS_TASKS:
            include.append("one current thesis")
        else:
            exclude.append("full thesis")
        if request.task in _PORTFOLIO_TASKS:
            include.append("current portfolio state")
        else:
            exclude.extend(["cost basis", "P&L", "position weight", "trade history"])
        if request.task == ContextTask.portfolio_review:
            include.extend(["bounded research summary for each held symbol", "bounded recent portfolio events"])
            exclude.append("all held symbols' full theses")

        return ContextPlan(
            task=request.task,
            symbol=request.symbol,
            include=include,
            exclude=exclude,
            reason=self._reason(request.task),
        )

    @staticmethod
    def _reason(task: ContextTask) -> str:
        reasons = {
            ContextTask.research_scan: "answer the research question without portfolio anchoring or thesis rewrite",
            ContextTask.event_intake: "classify new evidence before escalating to a thesis update",
            ContextTask.research_update: "update official coverage from current evidence without portfolio anchoring",
            ContextTask.thesis_review: "test the thesis as of a declared date without hindsight or P&L",
            ContextTask.portfolio_review: "screen the whole portfolio with bounded per-symbol research context",
            ContextTask.decision: "combine one company's research evidence with portfolio constraints",
            ContextTask.trade_record: "record execution facts without reopening investment reasoning",
            ContextTask.postmortem: "inspect only the affected artifact and violated contract",
        }
        return reasons[task]

    def build(self, request: ContextRequest) -> ContextPack:
        plan = self.plan(request)
        pack = ContextPack(task=request.task, symbol=request.symbol, excluded=plan.exclude.copy())

        if request.task == ContextTask.trade_record:
            self._add_approved_decision(pack, request)

        # A decision must reserve context for portfolio constraints before a
        # potentially long thesis consumes the budget.
        if request.task == ContextTask.decision:
            self._add_portfolio_context(pack, request)

        if request.task in _SYMBOL_TASKS and request.symbol:
            self._add_symbol_context(pack, request)

        if request.task in _PORTFOLIO_TASKS and request.task != ContextTask.decision:
            self._add_portfolio_context(pack, request)

        if pack.total_chars > request.max_chars:
            raise RuntimeError("context router exceeded its hard character budget")
        return pack

    def _add_approved_decision(self, pack: ContextPack, request: ContextRequest) -> None:
        assert request.decision_ref is not None
        root = self.research.paths.root.resolve(strict=False)
        reviews = self.research.paths.reviews.resolve(strict=False)
        candidate = Path(request.decision_ref)
        if candidate.is_absolute():
            raise ValueError("decision_ref must be repository-relative")
        path = (root / candidate).resolve(strict=False)
        if reviews not in path.parents:
            raise ValueError("decision_ref must point inside reviews/")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"decision record not found: {path}")
        content = path.read_text(encoding="utf-8")
        if not re.search(r"^\*\*Status:\*\*\s*approved\s*$", content, re.IGNORECASE | re.MULTILINE):
            raise ValueError("trade decision is not marked approved")
        if len(content) > request.max_chars - pack.total_chars:
            raise ValueError("approved decision does not fit the requested context budget")
        self._add_document(
            pack,
            LoadedDocument(
                role="approved_decision",
                path=str(path),
                content=content,
                chars=len(content),
            ),
        )

    def _add_portfolio_context(self, pack: ContextPack, request: ContextRequest) -> None:
        if self.portfolio is None:
            pack.warnings.append("portfolio context requested but no PortfolioService was provided")
            return
        state = self.portfolio.get_state()
        compact_state = self._compact_portfolio_state(state)
        state_chars = len(json.dumps(compact_state, ensure_ascii=False, separators=(",", ":")))
        if state_chars > request.max_chars - pack.total_chars:
            raise ValueError("context budget is too small for the compact current portfolio state")
        pack.portfolio_state = compact_state
        pack.total_chars += state_chars

        if request.task == ContextTask.portfolio_review:
            self._add_portfolio_research_overview(pack, state, request)
            events = self.portfolio.recent_events(
                after=request.portfolio_events_after,
                limit=request.max_portfolio_events,
            )
            for event in events:
                event_chars = len(event.model_dump_json())
                if event_chars > request.max_chars - pack.total_chars:
                    pack.warnings.append("recent portfolio events were truncated by the context budget")
                    break
                pack.portfolio_events.append(event.model_dump(mode="json"))
                pack.total_chars += event_chars

    @staticmethod
    def _compact_portfolio_state(state: Any) -> dict[str, Any]:
        return {
            "as_of": state.as_of.isoformat(),
            "base_currency": state.base_currency,
            "total_value": state.total_value,
            "total_cost": state.total_cost,
            "total_unrealized_pnl": state.total_unrealized_pnl,
            "cash_value": state.cash_value,
            "cash_pct": state.cash_pct,
            "valuation_complete": state.valuation_complete,
            "sector_exposure_pct": state.sector_exposure_pct,
            "region_exposure_pct": state.region_exposure_pct,
            "theme_exposure_pct": state.theme_exposure_pct,
            "warnings": state.warnings,
            "positions": [
                {
                    "symbol": item.symbol,
                    "quantity": item.quantity,
                    "avg_cost": item.avg_cost,
                    "currency": item.currency,
                    "market": item.market,
                    "sector": item.sector,
                    "region": item.region,
                    "theme_tags": item.theme_tags,
                    "risk_level": item.risk_level,
                    "current_price": item.current_price,
                    "quote_as_of": item.quote_as_of.isoformat() if item.quote_as_of else None,
                    "quote_source": item.quote_source,
                    "base_market_value": item.base_market_value,
                    "unrealized_pnl_pct": item.unrealized_pnl_pct,
                    "weight_pct": item.weight_pct,
                    "data_quality": item.data_quality,
                    "fx_rate_to_base": item.fx_rate_to_base,
                    "fx_as_of": item.fx_as_of.isoformat() if item.fx_as_of else None,
                    "fx_source": item.fx_source,
                }
                for item in state.positions
            ],
            "open_options": [
                {
                    "id": item.id,
                    "underlying_symbol": item.underlying_symbol,
                    "contracts": item.contracts,
                    "shares_per_contract": item.shares_per_contract,
                    "strike": item.strike,
                    "expiry_date": item.expiry_date.isoformat(),
                    "currency": item.currency,
                    "reserved_cash": item.reserved_cash,
                    "effective_entry_if_assigned": item.effective_entry_if_assigned,
                    "linked_decision_file": item.linked_decision_file,
                }
                for item in state.open_options
            ],
        }

    def _add_symbol_context(self, pack: ContextPack, request: ContextRequest) -> None:
        assert request.symbol is not None
        status = self.research.load_status(request.symbol)
        pack.research_status = status
        status_chars = len(status.model_dump_json())
        if status_chars > request.max_chars - pack.total_chars:
            raise ValueError("context budget is too small for research status")
        pack.total_chars += status_chars
        status_path = self.research.symbol_dir(request.symbol) / "status.json"
        if status_path.exists():
            pack.loaded_paths.append(str(status_path))
        else:
            pointer = self.research.symbol_dir(request.symbol) / "current.md"
            if pointer.exists():
                pack.loaded_paths.append(str(pointer))

        summary_path, summary = self.research.load_summary(request.symbol, status)
        if summary_path:
            remaining = request.max_chars - pack.total_chars
            cap = min(8_000, remaining)
            marker = "\n\n[Summary truncated by context router]"
            if cap > len(marker):
                bounded = summary[:cap]
                if len(summary) > len(bounded):
                    bounded = bounded[: cap - len(marker)] + marker
                self._add_document(pack, LoadedDocument(role="research_summary", path=str(summary_path), content=bounded, chars=len(bounded)))
            else:
                pack.warnings.append("research summary omitted because the context budget is exhausted")
        else:
            pack.warnings.append(
                f"no bounded summary found for {request.symbol}; use research_update to inspect the thesis and migrate the summary"
            )

        facts = self.research.load_facts(
            request.symbol,
            status=status,
            tags=request.topics,
            as_of=request.as_of,
            limit=request.max_facts,
        )
        sources = self.research.load_sources(request.symbol, status)
        sources_by_id = {source.source_id: source for source in sources}
        added_source_ids: set[str] = set()
        for fact in facts:
            needed_sources = [
                sources_by_id[source_id]
                for source_id in fact.source_ids
                if source_id in sources_by_id and source_id not in added_source_ids
            ]
            item_chars = len(fact.model_dump_json()) + sum(len(source.model_dump_json()) for source in needed_sources)
            if item_chars > request.max_chars - pack.total_chars:
                pack.warnings.append("research facts were truncated by the context budget")
                break
            missing_sources = sorted(set(fact.source_ids) - set(sources_by_id))
            if missing_sources:
                pack.warnings.append(f"fact {fact.fact_id} references missing source metadata: {missing_sources}")
            pack.facts.append(fact)
            pack.sources.extend(needed_sources)
            added_source_ids.update(source.source_id for source in needed_sources)
            pack.total_chars += item_chars
        sources_path = self.research.record_path(request.symbol, status.sources_path)
        if pack.sources and sources_path.exists():
            pack.loaded_paths.append(str(sources_path))

        facts_path = self.research.record_path(request.symbol, status.facts_path)
        if facts and facts_path.exists():
            pack.loaded_paths.append(str(facts_path))

        if request.task in _FULL_THESIS_TASKS:
            thesis = self.research.load_current_thesis(request.symbol)
            if thesis:
                path, text = thesis
                text, removed_lines = self.research.thesis_research_view(text)
                if removed_lines:
                    pack.warnings.append(
                        f"removed {removed_lines} portfolio-specific lines from the thesis research view"
                    )
                remaining = request.max_chars - pack.total_chars
                marker = "\n\n[Current thesis truncated by context router; increase max_chars for the complete version]"
                if remaining <= len(marker):
                    pack.warnings.append("current thesis omitted because the context budget is exhausted")
                else:
                    bounded = text
                    if len(text) > remaining:
                        bounded = text[: remaining - len(marker)] + marker
                        pack.warnings.append("current thesis was truncated by the context budget")
                    self._add_document(pack, LoadedDocument(role="current_thesis", path=str(path), content=bounded, chars=len(bounded)))
            else:
                pack.warnings.append(f"no current thesis found for {request.symbol}")

    def _add_portfolio_research_overview(self, pack: ContextPack, state: Any, request: ContextRequest) -> None:
        for position in state.positions:
            symbol = position.symbol.upper()
            if symbol.startswith("CASH"):
                continue
            try:
                status = self.research.load_status(symbol)
                summary_path, summary = self.research.load_summary(symbol, status)
            except (FileNotFoundError, ValueError):
                pack.warnings.append(f"no research status for held symbol {symbol}")
                continue
            if not summary:
                pack.warnings.append(f"no bounded research summary for held symbol {symbol}")
                continue
            bounded = summary[:3_000]
            item_chars = len(status.model_dump_json()) + len(bounded)
            if item_chars > request.max_chars - pack.total_chars:
                pack.warnings.append("portfolio research overview reached context budget; remaining symbols were not loaded")
                break
            pack.research_overview.append(ResearchOverview(symbol=symbol, status=status, summary=bounded))
            pack.total_chars += item_chars
            if summary_path:
                pack.loaded_paths.append(str(summary_path))
            status_path = self.research.symbol_dir(symbol) / "status.json"
            pointer_path = self.research.symbol_dir(symbol) / "current.md"
            if status_path.exists():
                pack.loaded_paths.append(str(status_path))
            elif pointer_path.exists():
                pack.loaded_paths.append(str(pointer_path))

    @staticmethod
    def _add_document(pack: ContextPack, document: LoadedDocument) -> None:
        pack.documents.append(document)
        pack.loaded_paths.append(document.path)
        pack.total_chars += document.chars
