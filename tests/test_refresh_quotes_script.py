from __future__ import annotations

import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from harness.portfolio.market_data import QuoteObservation, RefreshReport
from harness.portfolio.store import PortfolioStore

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_quotes.py"


def load_script():
    spec = importlib.util.spec_from_file_location("refresh_quotes_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(
        self,
        errors: list[str] | None = None,
        *,
        missing_symbols: tuple[str, ...] = (),
        currency: str = "USD",
        as_of: datetime | None = None,
    ):
        self.errors = errors or []
        self.missing_symbols = missing_symbols
        self.currency = currency
        self.as_of = as_of

    def refresh_portfolio(self, symbols, fx_pairs=()):
        now = self.as_of or datetime.now(timezone.utc)
        observed = [
            QuoteObservation(symbol=symbol, price=100, currency=self.currency, as_of=now, source="fake", source_ref=f"fake:{symbol}")
            for symbol in symbols
            if symbol not in self.missing_symbols
        ]
        return RefreshReport(observed=observed, errors=self.errors, as_of=now)


@pytest.fixture
def store(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    return store


def test_refresh_records_snapshot_by_default(harness_paths, store):
    assert load_script().main([], paths=harness_paths, client=FakeClient()) == 0

    snapshots = store.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].total_value == 2_000


def test_refresh_rerun_same_day_overwrites_snapshot(harness_paths, store):
    script = load_script()
    script.main([], paths=harness_paths, client=FakeClient())
    script.main([], paths=harness_paths, client=FakeClient())

    assert len(store.list_snapshots()) == 1


def test_refresh_no_record_skips_snapshot(harness_paths, store):
    assert load_script().main(["--no-record"], paths=harness_paths, client=FakeClient()) == 0

    assert store.list_snapshots() == []
    assert "ABC" in store.latest_quotes()


def test_refresh_with_pull_errors_does_not_record_snapshot(harness_paths, store):
    result = load_script().main([], paths=harness_paths, client=FakeClient(errors=["XYZ: timeout"]))

    assert result == 1
    assert store.list_snapshots() == []


@pytest.mark.parametrize(
    ("currency", "missing_symbols", "warning"),
    [
        ("USD", ("ABC",), "missing_price"),
        ("CNY", (), "missing_fx_rate:CNY->USD"),
    ],
)
def test_refresh_incomplete_valuation_without_cash_pct_skips_snapshot(
    harness_paths, capsys, currency, missing_symbols, warning
):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90, currency=currency)

    result = load_script().main(
        [],
        paths=harness_paths,
        client=FakeClient(missing_symbols=missing_symbols, currency=currency),
    )

    assert result == 1
    assert store.list_snapshots() == []
    assert not any(event.event_type == "snapshot_recorded" for event in store.list_events())
    output = capsys.readouterr().out
    assert "cash=0.0 (N/A)" in output
    assert "portfolio valuation incomplete" in output
    assert warning in output


@pytest.mark.parametrize(
    ("observed_at", "expected_day"),
    [
        (datetime(2026, 10, 9, 15, 59, tzinfo=timezone.utc), date(2026, 10, 9)),
        (datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc), date(2026, 10, 10)),
    ],
)
def test_refresh_snapshot_uses_beijing_date_for_record_and_notes(
    harness_paths, store, monkeypatch, observed_at, expected_day
):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return observed_at.astimezone(tz) if tz else observed_at.replace(tzinfo=None)

    monkeypatch.setattr("harness.portfolio.service.datetime", FixedDateTime)

    result = load_script().main([], paths=harness_paths, client=FakeClient(as_of=observed_at))

    assert result == 0
    snapshot = store.list_snapshots()[0]
    assert snapshot.snapshot_date == expected_day
    assert snapshot.notes == f"refresh_quotes {expected_day}"


def test_refresh_accepts_legacy_record_argument(harness_paths, store):
    assert load_script().main(["--record"], paths=harness_paths, client=FakeClient()) == 0

    assert len(store.list_snapshots()) == 1
    snapshot_events = [event for event in store.list_events() if event.event_type == "snapshot_recorded"]
    assert len(snapshot_events) == 1
    assert snapshot_events[0].source_ref == "refresh_quotes"
