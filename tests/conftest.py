from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from harness.settings import HarnessPaths


def create_research_record(root: Path, symbol: str = "ABC", summary: str = "Evidence-led summary") -> Path:
    symbol_dir = root / "coverage" / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    thesis_name = "thesis-2026-08-01.md"
    (symbol_dir / "current.md").write_text(thesis_name, encoding="utf-8")
    (symbol_dir / thesis_name).write_text(
        f"# {symbol} thesis\n\nFundamentals and invalidation conditions.",
        encoding="utf-8",
    )
    (symbol_dir / "summary.md").write_text(f"# {symbol}\n\n{summary}", encoding="utf-8")
    (symbol_dir / "status.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "symbol": symbol,
                "company_name": "Example Co",
                "current_thesis": thesis_name,
                "summary_path": "summary.md",
                "facts_path": "facts.jsonl",
                "sources_path": "sources.json",
                "legacy_layout": False,
            }
        ),
        encoding="utf-8",
    )
    (symbol_dir / "sources.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "sources": [
                    {
                        "source_id": "src-1",
                        "title": "Annual report",
                        "source_type": "filing",
                        "publisher": "Example Co",
                        "published_at": "2026-03-01",
                        "primary": True,
                        "url": "https://example.com/annual-report",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    fact = {
        "fact_id": "fact-1",
        "symbol": symbol,
        "fact_key": "revenue",
        "statement": "Revenue was 100",
        "fact_type": "reported",
        "value": 100,
        "unit": "USDm",
        "period": "FY2025",
        "available_at": "2026-08-01T00:00:00Z",
        "source_ids": ["src-1"],
        "locator": "p. 10",
        "tags": ["financials"],
        "recorded_at": datetime(2026, 8, 1, tzinfo=timezone.utc).isoformat(),
    }
    (symbol_dir / "facts.jsonl").write_text(json.dumps(fact) + "\n", encoding="utf-8")
    return symbol_dir


@pytest.fixture
def harness_root(tmp_path: Path) -> Path:
    for directory in ("coverage", "reviews", "data", "config"):
        (tmp_path / directory).mkdir()
    create_research_record(tmp_path)
    (tmp_path / "config" / "profile.json").write_text(
        json.dumps({"max_position_weight": 0.25, "min_cash_pct": 0.05}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def harness_paths(harness_root: Path) -> HarnessPaths:
    return HarnessPaths.discover(harness_root)
