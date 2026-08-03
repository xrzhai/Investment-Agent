from __future__ import annotations

import sqlite3

from harness.portfolio.store import PortfolioStore
from harness.validation import validate_workspace


def test_validation_detects_portfolio_facts_in_structured_research(harness_paths):
    summary = harness_paths.coverage / "ABC" / "summary.md"
    summary.write_text("# ABC\n\n我的持仓成本是 90，当前浮盈。", encoding="utf-8")
    PortfolioStore(paths=harness_paths).ensure_schema()

    report = validate_workspace(harness_paths.root)

    assert any(issue.code == "context.portfolio_fact_in_research" for issue in report.issues)
    assert report.error_count >= 1


def test_validation_accepts_clean_structured_research(harness_paths):
    PortfolioStore(paths=harness_paths).ensure_schema()

    report = validate_workspace(harness_paths.root)

    assert not any(issue.code.startswith("research.") and issue.severity == "error" for issue in report.issues)
    assert not any(issue.code == "context.portfolio_fact_in_research" for issue in report.issues)


def test_workspace_validation_does_not_migrate_legacy_database(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db_path = data / "investment.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE positions(id INTEGER PRIMARY KEY, symbol TEXT);
        CREATE TABLE option_contracts(id INTEGER PRIMARY KEY, status TEXT);
        CREATE TABLE snapshots(id INTEGER PRIMARY KEY, snapshot_date DATE);
        CREATE TABLE cashflow_events(id INTEGER PRIMARY KEY);
        """
    )
    connection.close()

    report = validate_workspace(tmp_path)
    connection = sqlite3.connect(db_path)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()

    assert any(issue.code == "portfolio.event_log_not_initialized" for issue in report.issues)
    assert "portfolio_events" not in tables
    assert "quotes" not in tables
    assert "instrument_metadata" not in tables


def test_legacy_thesis_contamination_is_warned_not_rewritten(tmp_path):
    symbol_dir = tmp_path / "coverage" / "ABC"
    symbol_dir.mkdir(parents=True)
    (symbol_dir / "current.md").write_text("v1.md", encoding="utf-8")
    original = "# ABC\n\n## 头寸管理原则\n当前权重 20%\n"
    thesis = symbol_dir / "v1.md"
    thesis.write_text(original, encoding="utf-8")

    report = validate_workspace(tmp_path)

    assert any(issue.code == "context.legacy_thesis_needs_separation" for issue in report.issues)
    assert thesis.read_text(encoding="utf-8") == original
