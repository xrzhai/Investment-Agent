from __future__ import annotations

import sqlite3
from pathlib import Path

from harness.models import Severity, ValidationIssue, ValidationReport
from harness.research.store import ResearchStore
from harness.settings import HarnessPaths


def validate_workspace(root: str | Path | None = None) -> ValidationReport:
    """Run read-only structural checks across research and portfolio domains."""

    paths = HarnessPaths.discover(root)
    research = ResearchStore(paths)
    issues: list[ValidationIssue] = []
    for symbol in research.list_symbols():
        issues.extend(research.validate_symbol(symbol))
    issues.extend(_validate_portfolio_db(paths.portfolio_db))
    return ValidationReport(issues=issues)


def _validate_portfolio_db(db_path: Path) -> list[ValidationIssue]:
    if not db_path.exists():
        return [
            ValidationIssue(
                code="portfolio.db_missing",
                severity=Severity.info,
                message="portfolio database does not exist yet",
                path=str(db_path),
            )
        ]

    issues: list[ValidationIssue] = []
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for table in ("positions", "option_contracts", "snapshots", "cashflow_events"):
            if table not in tables:
                issues.append(
                    ValidationIssue(
                        code="portfolio.table_missing",
                        severity=Severity.error,
                        message=f"required table is missing: {table}",
                        path=str(db_path),
                    )
                )
        if "positions" in tables:
            duplicates = connection.execute(
                "SELECT symbol, COUNT(*) AS count FROM positions GROUP BY symbol HAVING COUNT(*) > 1"
            ).fetchall()
            for row in duplicates:
                issues.append(
                    ValidationIssue(
                        code="portfolio.duplicate_position",
                        severity=Severity.error,
                        message=f"{row['symbol']} has {row['count']} current position rows",
                        path=str(db_path),
                    )
                )
        if "snapshots" in tables:
            duplicates = connection.execute(
                "SELECT snapshot_date, COUNT(*) AS count FROM snapshots GROUP BY snapshot_date HAVING COUNT(*) > 1"
            ).fetchall()
            for row in duplicates:
                issues.append(
                    ValidationIssue(
                        code="portfolio.duplicate_snapshot_date",
                        severity=Severity.warning,
                        message=f"{row['snapshot_date']} has {row['count']} historical snapshot rows",
                        path=str(db_path),
                    )
                )
        if "option_contracts" in tables:
            invalid = connection.execute(
                "SELECT id, status FROM option_contracts WHERE status NOT IN ('open','assigned','expired','closed')"
            ).fetchall()
            for row in invalid:
                issues.append(
                    ValidationIssue(
                        code="portfolio.option_status_invalid",
                        severity=Severity.error,
                        message=f"option #{row['id']} has invalid status {row['status']!r}",
                        path=str(db_path),
                    )
                )
        if "portfolio_events" not in tables:
            issues.append(
                ValidationIssue(
                    code="portfolio.event_log_not_initialized",
                    severity=Severity.info,
                    message="append-only event log has not been initialized; run an explicit migration before the next mutation",
                    path=str(db_path),
                )
            )
        if "quotes" not in tables:
            issues.append(
                ValidationIssue(
                    code="portfolio.quote_log_not_initialized",
                    severity=Severity.info,
                    message="structured quote observations have not been initialized",
                    path=str(db_path),
                )
            )
        elif "positions" in tables:
            missing_quotes = [
                row["symbol"]
                for row in connection.execute(
                    "SELECT p.symbol FROM positions p LEFT JOIN quotes q ON q.symbol=p.symbol "
                    "WHERE p.symbol NOT LIKE 'CASH_%' GROUP BY p.symbol HAVING COUNT(q.id)=0 ORDER BY p.symbol"
                ).fetchall()
            ]
            if missing_quotes:
                issues.append(
                    ValidationIssue(
                        code="portfolio.structured_quotes_missing",
                        severity=Severity.warning,
                        message=f"positions rely on legacy cached prices instead of sourced quote rows: {', '.join(missing_quotes)}",
                        path=str(db_path),
                    )
                )
            foreign_currencies = {
                row["currency"]
                for row in connection.execute(
                    "SELECT DISTINCT COALESCE(NULLIF(currency,''), CASE WHEN symbol LIKE '%.SH' OR symbol LIKE '%.SZ' THEN 'CNY' WHEN symbol LIKE '%.HK' THEN 'HKD' ELSE 'USD' END) AS currency FROM positions"
                ).fetchall()
                if row["currency"] != "USD"
            }
            missing_fx = [
                currency
                for currency in sorted(foreign_currencies)
                if connection.execute(
                    "SELECT 1 FROM quotes WHERE symbol=? LIMIT 1",
                    (f"FX:{currency}/USD",),
                ).fetchone()
                is None
            ]
            if missing_fx:
                issues.append(
                    ValidationIssue(
                        code="portfolio.structured_fx_missing",
                        severity=Severity.warning,
                        message=f"portfolio valuation needs sourced FX observations for: {', '.join(missing_fx)}",
                        path=str(db_path),
                    )
                )
        if "instrument_metadata" not in tables:
            issues.append(
                ValidationIssue(
                    code="portfolio.instrument_metadata_not_initialized",
                    severity=Severity.info,
                    message="persistent instrument classifications have not been initialized",
                    path=str(db_path),
                )
            )
    finally:
        connection.close()
    return issues
