from __future__ import annotations

import json
from datetime import date, datetime, timezone

from harness.portfolio.models import InvestorProfile
from harness.portfolio.policy import evaluate_policy
from harness.portfolio.service import PortfolioService
from harness.portfolio.store import PortfolioStore


def test_state_uses_sourced_quote_and_explicit_fx(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    store.set_position_baseline(symbol="600000.SH", quantity=100, avg_cost=9, market="CN_A", currency="CNY")
    store.record_quote(
        symbol="ABC",
        price=100,
        currency="USD",
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
        source="exchange_close",
    )
    store.record_quote(
        symbol="600000.SH",
        price=10,
        currency="CNY",
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
        source="exchange_close",
    )
    service = PortfolioService(store, paths=harness_paths)

    partial = service.get_state()
    complete = service.get_state(fx_rates_to_base={"CNY": 0.14})

    assert partial.valuation_complete is False
    assert partial.total_cost is None
    assert complete.valuation_complete is True
    assert complete.total_value == 2_140
    assert complete.priced_position_count == 3
    assert next(item for item in complete.positions if item.symbol == "ABC").quote_source == "exchange_close"


def test_state_prefers_persisted_sourced_fx_when_no_rate_is_supplied(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_CNY", quantity=1_000, avg_cost=1)
    observed_at = datetime(2026, 8, 3, tzinfo=timezone.utc)
    store.record_fx_rate(
        currency="CNY",
        base_currency="USD",
        rate_to_base=0.14,
        as_of=observed_at,
        source="central_bank_reference",
        source_ref="fx-source",
    )

    state = PortfolioService(store, paths=harness_paths).get_state()
    cash = state.positions[0]

    assert state.total_value == 140
    assert cash.fx_rate_to_base == 0.14
    assert cash.fx_as_of == observed_at
    assert cash.fx_source == "central_bank_reference"


def test_snapshot_is_compact_and_upserts_same_date(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    store.record_quote(
        symbol="ABC",
        price=100,
        currency="USD",
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
        source="exchange_close",
    )
    service = PortfolioService(store, paths=harness_paths)

    snapshot, _ = service.record_snapshot(snapshot_date=date(2026, 8, 3), source_ref="review.md")
    service.record_snapshot(snapshot_date=date(2026, 8, 3), notes="updated", source_ref="review.md")

    assert len(store.list_snapshots()) == 1
    assert len(snapshot.positions_json) < 1_000
    assert json.loads(snapshot.positions_json)[0]["symbol"] in {"ABC", "CASH_USD"}


def test_snapshot_twr_uses_base_currency_cashflow_not_local_amount(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    service = PortfolioService(store, paths=harness_paths)

    service.record_snapshot(snapshot_date=date(2026, 8, 1), source_ref="baseline")
    store.record_cashflow(
        amount_local=700,
        currency="CNY",
        fx_rate_to_base=1 / 7,
        fx_as_of=datetime(2026, 8, 2, tzinfo=timezone.utc),
        fx_source="historical_close",
        description="CNY deposit",
        event_date=date(2026, 8, 2),
        cashflow_ref="cashflow-cny-twr-test",
    )

    snapshot, _ = service.record_snapshot(
        snapshot_date=date(2026, 8, 2),
        fx_rates_to_base={"CNY": 1 / 7},
        source_ref="twr-check",
    )

    assert snapshot.total_value == 1_100
    assert snapshot.daily_return_pct == 0


def test_policy_reports_concentration_without_recommending_a_trade(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=100, avg_cost=90)
    store.record_quote(
        symbol="ABC",
        price=100,
        currency="USD",
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
        source="exchange_close",
    )
    state = PortfolioService(store, paths=harness_paths).get_state()

    report = evaluate_policy(state, InvestorProfile(max_position_weight=0.25, min_cash_pct=0.05))

    concentration = next(signal for signal in report.signals if signal.signal_type == "position_concentration")
    assert concentration.severity == "violation"
    assert "sell" not in concentration.message.lower()


def test_state_aggregates_sector_region_and_theme_exposure(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_instrument_metadata(
        symbol="ABC",
        sector="Technology",
        region="US",
        theme_tags=["AI"],
        source="coverage_status",
    )
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    store.record_quote(
        symbol="ABC",
        price=100,
        currency="USD",
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
        source="exchange_close",
    )

    state = PortfolioService(store, paths=harness_paths).get_state()

    assert state.sector_exposure_pct == {"Technology": 50.0}
    assert state.region_exposure_pct == {"US": 50.0}
    assert state.theme_exposure_pct == {"AI": 50.0}


def test_historical_state_never_uses_future_quote(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    store.record_quote(
        symbol="ABC",
        price=100,
        currency="USD",
        as_of=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source="exchange_close",
    )
    store.record_quote(
        symbol="ABC",
        price=200,
        currency="USD",
        as_of=datetime(2026, 8, 5, tzinfo=timezone.utc),
        source="exchange_close",
    )

    state = PortfolioService(store, paths=harness_paths).get_state(
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc)
    )

    assert state.positions[0].current_price == 100
    assert state.total_value == 1_000
    stale = PortfolioService(store, paths=harness_paths).get_state(
        as_of=datetime(2026, 8, 20, tzinfo=timezone.utc)
    )
    assert any(item.startswith("stale_quote:") for item in stale.positions[0].data_quality)
