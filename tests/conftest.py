from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.settings import HarnessPaths


def create_coverage_record(root: Path, symbol: str = "ABC") -> Path:
    symbol_dir = root / "research" / "coverage" / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    thesis_name = "thesis-2026-08-01.md"
    (symbol_dir / "current.md").write_text(thesis_name, encoding="utf-8")
    (symbol_dir / thesis_name).write_text(
        f"# {symbol} thesis\n\nFundamentals and invalidation conditions.",
        encoding="utf-8",
    )
    (symbol_dir / "summary.md").write_text(f"# {symbol}\n\nEvidence-led summary", encoding="utf-8")
    return symbol_dir


@pytest.fixture
def harness_root(tmp_path: Path) -> Path:
    for directory in ("research/coverage", "research/topics", "portfolio/data"):
        (tmp_path / directory).mkdir(parents=True)
    create_coverage_record(tmp_path)
    (tmp_path / "research" / "context.md").write_text(
        "# Research Context\n\nUnderstand the business before selecting evidence.",
        encoding="utf-8",
    )
    (tmp_path / "portfolio" / "profile.json").write_text(
        json.dumps({"max_position_weight": 0.25, "min_cash_pct": 0.05}),
        encoding="utf-8",
    )
    (tmp_path / "portfolio" / "principles.md").write_text(
        "# Investment Principles\n\nValuation and portfolio constraints are separate lenses.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def harness_paths(harness_root: Path) -> HarnessPaths:
    return HarnessPaths.discover(harness_root)
