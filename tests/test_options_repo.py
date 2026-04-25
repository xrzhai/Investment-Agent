import unittest
from datetime import date
from types import SimpleNamespace

from app.repositories.options_repo import (
    _require_open_status,
    _validate_new_contract_dates,
    compute_open_put_exposure,
    derive_open_put_metrics,
)


class OptionsRepoTests(unittest.TestCase):
    def test_derive_open_put_metrics_uses_cash_secured_and_premium_adjusted_entry(self):
        metrics = derive_open_put_metrics(
            strike=40.0,
            contracts=1,
            premium_per_share=11.53,
            shares_per_contract=100,
            fees=0.0,
        )

        self.assertEqual(metrics["premium_total"], 1153.0)
        self.assertEqual(metrics["reserved_cash"], 4000.0)
        self.assertEqual(metrics["net_cash_obligation"], 2847.0)
        self.assertEqual(metrics["effective_entry_if_assigned"], 28.47)

    def test_compute_open_put_exposure_combines_option_with_existing_spot_position(self):
        spot_positions = [
            SimpleNamespace(
                symbol="BMNR",
                quantity=300.0,
                avg_cost=31.48,
                current_price=22.14,
                base_market_value=6642.0,
                currency="USD",
                market="US",
            ),
            SimpleNamespace(
                symbol="CASH_USD",
                quantity=544.67,
                avg_cost=1.0,
                current_price=1.0,
                base_market_value=544.67,
                currency="USD",
                market="US",
            ),
        ]
        option_rows = [
            SimpleNamespace(
                id=1,
                underlying_symbol="BMNR",
                option_type="put",
                side="short",
                contracts=1,
                shares_per_contract=100,
                strike=40.0,
                expiry_date=date(2026, 6, 18),
                opened_date=None,
                premium_per_share=11.53,
                premium_total=1153.0,
                fees=0.0,
                currency="USD",
                market="US",
                status="open",
                reserved_cash=4000.0,
                effective_entry_if_assigned=28.47,
                intent="lower_price_entry",
                notes="",
                linked_decision_file="",
                closed_date=None,
                assigned_date=None,
                assignment_price=None,
                realized_premium=None,
            )
        ]

        summary = compute_open_put_exposure(
            spot_positions=spot_positions,
            option_rows=option_rows,
            total_portfolio_value_usd=100000.0,
        )

        self.assertEqual(summary["contract_count"], 1)
        self.assertEqual(summary["totals"]["reserved_cash_by_currency"]["USD"], 4000.0)
        self.assertEqual(summary["totals"]["cash_by_currency"]["USD"], 544.67)
        self.assertEqual(summary["totals"]["cash_gap_vs_reserved_by_currency"]["USD"], -3455.33)

        contract = summary["contracts"][0]
        self.assertEqual(contract["underlying_symbol"], "BMNR")
        self.assertEqual(contract["assigned_total_shares"], 400.0)
        self.assertEqual(contract["assigned_avg_cost"], 30.7275)
        self.assertEqual(contract["spot_price"], 22.14)
        self.assertEqual(contract["moneyness"], "itm")
        self.assertIsNotNone(contract["days_to_expiry"])

    def test_validate_new_contract_dates_rejects_open_after_expiry(self):
        with self.assertRaises(ValueError):
            _validate_new_contract_dates(date(2026, 6, 19), date(2026, 6, 18))

    def test_require_open_status_rejects_non_open_contract(self):
        with self.assertRaises(ValueError):
            _require_open_status(SimpleNamespace(id=7, status="expired"), "assign")


if __name__ == "__main__":
    unittest.main()
