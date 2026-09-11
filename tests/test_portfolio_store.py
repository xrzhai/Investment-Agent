from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from harness.portfolio.store import PortfolioStore


def test_trade_requires_decision_and_updates_cash_atomically(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)

    with pytest.raises(ValueError, match="decision_ref"):
        store.record_trade(
            symbol="ABC",
            side="buy",
            quantity=1,
            price=100,
            execution_ref="broker-unauthorized-1",
        )

    result = store.record_trade(
        symbol="ABC",
        side="buy",
        quantity=10,
        price=100,
        decision_ref="reviews/decisions/ABC-2026-08-03.md",
        execution_ref="broker-trade-1",
    )

    assert result.new_quantity == 20
    assert result.new_avg_cost == 95
    assert store.get_position("CASH_USD").quantity == 9_000
    assert store.list_events(limit=1)[0].event_type == "trade"
    with pytest.raises(ValueError, match="already recorded"):
        store.record_trade(
            symbol="ABC",
            side="buy",
            quantity=10,
            price=100,
            decision_ref="reviews/decisions/ABC-2026-08-03.md",
            execution_ref="broker-trade-1",
        )
    assert store.get_position("ABC").quantity == 20
    assert store.get_position("CASH_USD").quantity == 9_000


def test_insufficient_cash_rolls_back_trade(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="CASH_USD", quantity=100, avg_cost=1)

    with pytest.raises(ValueError, match="insufficient CASH_USD"):
        store.record_trade(
            symbol="ABC",
            side="buy",
            quantity=10,
            price=100,
            decision_ref="decision.md",
            execution_ref="broker-trade-2",
        )

    assert store.get_position("ABC") is None
    assert store.get_position("CASH_USD").quantity == 100


def test_short_put_assignment_updates_contract_position_and_cash(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    contract_id, _ = store.record_option_open(
        underlying_symbol="ABC",
        expiry_date=date(2026, 9, 18),
        strike=50,
        contracts=1,
        premium_per_share=1,
        opened_date=date(2026, 8, 3),
        decision_ref="reviews/decisions/ABC-put.md",
        execution_ref="broker-option-open-1",
    )

    store.transition_option(
        contract_id=contract_id,
        new_status="assigned",
        event_date=date(2026, 9, 18),
        execution_ref="broker-confirmation-1",
    )

    assert store.get_position("ABC").quantity == 100
    assert store.get_position("ABC").avg_cost == 50
    assert store.get_position("CASH_USD").quantity == 5_100
    assert store.list_option_contracts()[0].status == "assigned"
    event_types = [event.event_type for event in store.list_events()]
    assert event_types[0] == "option_assigned"
    assert set(event_types) == {"option_assigned", "option_opened", "position_baseline"}


def test_quote_observation_preserves_source_and_as_of(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    observed_at = datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)

    quote = store.record_quote(
        symbol="ABC",
        price=123.45,
        currency="USD",
        as_of=observed_at,
        source="broker_statement",
        source_ref="statement.pdf#p1",
    )

    assert quote.as_of == observed_at
    assert store.latest_quotes()["ABC"].source_ref == "statement.pdf#p1"
    store.record_quote(
        symbol="ABC",
        price=123.45,
        currency="USD",
        as_of=observed_at,
        source="broker_statement",
        source_ref="statement.pdf#p1",
    )
    assert [event.event_type for event in store.list_events()] == ["quote_observed"]
    store.record_quote(
        symbol="ABC",
        price=124.0,
        currency="USD",
        as_of=observed_at,
        source="broker_statement",
        source_ref="statement-correction.pdf#p1",
    )
    events = store.list_events()
    assert [event.event_type for event in events] == ["quote_corrected", "quote_observed"]
    assert events[0].payload["previous_price"] == 123.45


def test_correction_event_timestamp_amendment_preserves_audit_context(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    occurred_at = datetime(2026, 8, 5, 1, 0, tzinfo=timezone.utc)
    historical_at = datetime(2026, 7, 23, 0, 0, tzinfo=timezone.utc)
    store.set_position_baseline(
        symbol="CASH_CNY",
        quantity=2_252,
        avg_cost=0.1479,
        market="CN_A",
        currency="CNY",
    )

    store.record_trade(
        symbol="CASH_CNY",
        side="sell",
        quantity=2_252,
        price=1,
        currency="CNY",
        market="CN_A",
        occurred_at=occurred_at,
        source="correction",
        execution_ref="user-confirmed-cny-cash-clear-test",
        correction_reason="historical cash withdrawal",
        adjust_cash_position=False,
    )

    store.amend_correction_event_occurred_at(
        event_id="trade:user-confirmed-cny-cash-clear-test",
        occurred_at=historical_at,
        amendment_reason="user supplied the original withdrawal date",
        source_ref="user-confirmed-cny-cash-clear-test:date-amendment",
    )

    event = next(
        event
        for event in store.list_events(limit=10)
        if event.event_id == "trade:user-confirmed-cny-cash-clear-test"
    )
    assert event.occurred_at == historical_at
    assert event.recorded_at >= occurred_at
    assert event.payload["amendments"][0]["previous_occurred_at"] == occurred_at.isoformat()


def test_event_queries_are_bounded(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")

    with pytest.raises(ValueError, match="between 1 and 1000"):
        store.list_events(limit=10_000)


def test_instrument_metadata_survives_position_close(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_instrument_metadata(
        symbol="ABC",
        sector="Technology",
        region="US",
        theme_tags=["AI", "Cloud"],
        source="research_classification",
        source_ref="coverage/ABC/status.json",
    )
    store.set_instrument_metadata(
        symbol="ABC",
        risk_level="medium",
        source="research_classification",
        source_ref="coverage/ABC/status.json",
    )
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)

    assert store.get_position("ABC").theme_tags == ["AI", "Cloud"]
    store.record_trade(
        symbol="ABC",
        side="sell",
        quantity=10,
        price=100,
        decision_ref="decision.md",
        execution_ref="broker-close-1",
    )

    metadata = store.get_instrument_metadata("ABC")
    assert metadata.sector == "Technology"
    assert metadata.risk_level == "medium"
    assert store.get_position("ABC") is None


def test_market_and_currency_are_inferred_for_legacy_symbol_conventions(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")

    store.set_position_baseline(symbol="000975.SZ", quantity=100, avg_cost=10)
    store.set_position_baseline(symbol="0700.HK", quantity=100, avg_cost=500)

    assert (store.get_position("000975.SZ").market, store.get_position("000975.SZ").currency) == ("CN_A", "CNY")
    assert (store.get_position("0700.HK").market, store.get_position("0700.HK").currency) == ("HK", "HKD")


def test_legacy_bootstrap_is_idempotent_and_preserves_classification(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    with store.connect() as connection:
        connection.execute(
            "UPDATE positions SET sector='Technology', region='US', theme_tags='AI,Cloud' WHERE symbol='ABC'"
        )
        connection.commit()

    first = store.bootstrap_legacy_events()
    second = store.bootstrap_legacy_events()

    assert first == 1
    assert second == 0
    metadata = store.get_instrument_metadata("ABC")
    assert metadata.sector == "Technology"
    assert metadata.theme_tags == ["AI", "Cloud"]


def test_existing_market_and_currency_are_not_overwritten_by_symbol_default(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="SAP", quantity=10, avg_cost=200, market="EU", currency="EUR")

    store.set_position_baseline(symbol="SAP", quantity=12, avg_cost=205)

    position = store.get_position("SAP")
    assert position.market == "EU"
    assert position.currency == "EUR"


def test_cashflow_reference_prevents_duplicate_deposit(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)

    store.record_cashflow(
        amount_usd=500,
        description="deposit",
        cashflow_ref="bank-transfer-1",
    )
    with pytest.raises(ValueError, match="already recorded"):
        store.record_cashflow(
            amount_usd=500,
            description="deposit",
            cashflow_ref="bank-transfer-1",
        )

    assert store.get_position("CASH_USD").quantity == 1_500
    cashflow = store.list_cashflows()[0]
    assert cashflow.amount_local == 500
    assert cashflow.currency == "USD"
    assert cashflow.amount_base == 500
    assert cashflow.amount_usd == 500
    assert cashflow.flow_scope == "external"
    assert cashflow.flow_type == "deposit"


def test_multicurrency_cashflow_keeps_local_and_base_amounts_separate(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")
    store.set_position_baseline(
        symbol="CASH_CNY",
        quantity=2_252,
        avg_cost=1,
        market="CN_A",
        currency="CNY",
    )

    store.record_cashflow(
        amount_local=-2_252,
        currency="CNY",
        fx_rate_to_base=0.1477,
        fx_as_of=datetime(2026, 7, 23, tzinfo=timezone.utc),
        fx_source="historical_close",
        description="CNY withdrawal",
        event_date=date(2026, 7, 23),
        cashflow_ref="cash-withdrawal-cny-test",
    )

    cashflow = store.list_cashflows()[0]
    assert cashflow.amount_local == -2_252
    assert cashflow.currency == "CNY"
    assert cashflow.amount_base == pytest.approx(-332.6204)
    assert cashflow.amount_usd == pytest.approx(-332.6204)
    assert cashflow.fx_rate_to_base == 0.1477
    assert cashflow.fx_status == "calculated_from_rate"
    assert cashflow.flow_type == "withdrawal"
    assert store.get_position("CASH_CNY").quantity == 0


def test_non_base_cashflow_requires_event_time_conversion(tmp_path):
    store = PortfolioStore(db_path=tmp_path / "portfolio.db")

    with pytest.raises(ValueError, match="amount_base or fx_rate_to_base"):
        store.record_cashflow(
            amount_local=700,
            currency="CNY",
            description="missing FX",
            cashflow_ref="cashflow-missing-fx",
        )
