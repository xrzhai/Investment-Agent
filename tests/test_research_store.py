from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from harness.research.models import FactRecord, SourceRecord
from harness.research.store import ResearchStore


def test_structured_fact_keeps_source_lineage(harness_paths):
    store = ResearchStore(harness_paths)

    fact = store.load_facts("ABC")[0]
    source = store.load_sources("ABC")[0]

    assert fact.source_ids == [source.source_id]
    assert source.primary is True
    assert not any(issue.severity.value == "error" for issue in store.validate_symbol("ABC"))


def test_unsafe_record_path_is_rejected(harness_paths):
    status_path = harness_paths.coverage / "ABC" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["facts_path"] = "../outside.jsonl"
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    issues = ResearchStore(harness_paths).validate_symbol("ABC")

    assert any(issue.code == "research.record_path_unsafe" for issue in issues)
    assert any(issue.code == "research.facts_invalid" for issue in issues)


def test_safe_writes_are_idempotent_and_supersede_logically(harness_paths):
    store = ResearchStore(harness_paths)
    source = SourceRecord(
        source_id="src-2",
        title="Interim update",
        source_type="earnings_release",
        publisher="Example Co",
        published_at="2026-08-02",
        url="https://example.com/interim",
        primary=True,
    )
    assert store.add_source("ABC", source) is True
    assert store.add_source("ABC", source) is False
    fact = FactRecord(
        fact_id="fact-2",
        symbol="ABC",
        fact_key="revenue",
        statement="Revenue was revised to 110",
        fact_type="reported",
        value=110,
        unit="USDm",
        period="FY2025",
        source_ids=["src-2"],
        locator="table 1",
        supersedes="fact-1",
        tags=["financials"],
        recorded_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert store.append_fact("ABC", fact) is True
    assert store.append_fact("ABC", fact) is False
    assert [item.fact_id for item in store.load_facts("ABC")] == ["fact-2"]
    assert "fact-1" in (harness_paths.coverage / "ABC" / "facts.jsonl").read_text(encoding="utf-8")


def test_fact_write_rejects_missing_source(harness_paths):
    fact = FactRecord(
        fact_id="fact-missing-source",
        symbol="ABC",
        fact_key="guidance",
        statement="Guidance changed",
        fact_type="guidance",
        period="FY2026",
        source_ids=["does-not-exist"],
        recorded_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="missing sources"):
        ResearchStore(harness_paths).append_fact("ABC", fact)


def test_scaffolding_legacy_thesis_does_not_claim_migration_complete(harness_paths):
    symbol_dir = harness_paths.coverage / "LEG"
    symbol_dir.mkdir()
    (symbol_dir / "current.md").write_text("v1.md", encoding="utf-8")
    (symbol_dir / "v1.md").write_text("# Legacy thesis", encoding="utf-8")

    ResearchStore(harness_paths).ensure_scaffold("LEG")
    status = ResearchStore(harness_paths).load_status("LEG")
    summary = (symbol_dir / "summary.md").read_text(encoding="utf-8")

    assert status.legacy_layout is True
    assert "当前理解" in summary
    assert "估值读法" in summary
    assert "尚未完成结构化迁移" in summary


def test_historical_context_filters_by_information_availability(harness_paths):
    store = ResearchStore(harness_paths)

    before_release = store.load_facts("ABC", as_of=date(2026, 7, 31))
    after_release = store.load_facts("ABC", as_of=date(2026, 8, 1))

    assert before_release == []
    assert [fact.fact_id for fact in after_release] == ["fact-1"]


def test_fact_cannot_predate_its_source(harness_paths):
    fact = FactRecord(
        fact_id="fact-before-source",
        symbol="ABC",
        fact_key="revenue",
        statement="Impossible early availability",
        fact_type="reported",
        period="FY2025",
        available_at=date(2026, 1, 1),
        source_ids=["src-1"],
        recorded_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="precedes source publication"):
        ResearchStore(harness_paths).append_fact("ABC", fact)


def test_local_source_cannot_escape_symbol_directory(harness_paths):
    source = SourceRecord(
        source_id="unsafe-source",
        title="Unsafe",
        source_type="other",
        publisher="Unknown",
        published_at_unknown_reason="not published",
        local_path="../../secrets.txt",
    )

    with pytest.raises(ValueError, match="escapes symbol directory"):
        ResearchStore(harness_paths).add_source("ABC", source)
