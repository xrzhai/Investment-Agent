from __future__ import annotations

import sqlite3

from harness.portfolio.store import PortfolioStore
from harness.validation import validate_workspace


def test_validation_accepts_structured_research(harness_paths):
    PortfolioStore(paths=harness_paths).ensure_schema()

    report = validate_workspace(harness_paths.root)

    assert not any(issue.code.startswith("research.") and issue.severity == "error" for issue in report.issues)


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
