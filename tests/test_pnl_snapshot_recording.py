import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from app.tools.pnl_tools import _record_snapshot


class PnlSnapshotRecordingTests(unittest.TestCase):
    def test_record_snapshot_persists_cash_position_detail_daily_return_and_drawdown(self):
        state = {
            "total_value_usd": 1000.0,
            "positions": [
                {
                    "symbol": "AAA",
                    "base_market_value_usd": 600.0,
                    "weight_pct": 60.0,
                    "local_price": 60.0,
                },
                {
                    "symbol": "BBB",
                    "base_market_value_usd": 300.0,
                    "weight_pct": 30.0,
                    "local_price": 30.0,
                },
                {
                    "symbol": "CASH_USD",
                    "base_market_value_usd": 100.0,
                    "weight_pct": 10.0,
                    "local_price": 1.0,
                },
            ],
        }
        snapshots = [
            SimpleNamespace(snapshot_date=date(2026, 5, 1), total_value=1200.0),
            SimpleNamespace(snapshot_date=date(2026, 5, 4), total_value=900.0),
            # Existing same-day rows are overwritten by --record and should not be
            # treated as historical peaks when recomputing current drawdown.
            SimpleNamespace(snapshot_date=date(2026, 5, 5), total_value=2000.0),
        ]

        with patch("app.tools.pnl_tools.get_portfolio_state", return_value=state), \
             patch("app.tools.pnl_tools.list_snapshots_asc", return_value=snapshots), \
             patch("app.tools.pnl_tools.list_cashflows", return_value=[]), \
             patch("app.tools.pnl_tools.upsert_pnl_snapshot") as upsert:
            total = _record_snapshot(notes="test snapshot")

        self.assertEqual(total, 1000.0)
        upsert.assert_called_once()
        args, kwargs = upsert.call_args
        self.assertEqual(args, (1000.0,))
        self.assertEqual(kwargs["notes"], "test snapshot")
        self.assertEqual(kwargs["cash"], 100.0)
        self.assertEqual(kwargs["top_position_weight"], 60.0)
        self.assertEqual(kwargs["daily_return_pct"], 11.11)
        self.assertEqual(kwargs["max_drawdown_pct"], -25.0)

        persisted_positions = json.loads(kwargs["positions_json"])
        self.assertEqual([p["symbol"] for p in persisted_positions], ["AAA", "BBB", "CASH_USD"])
        self.assertEqual(persisted_positions[0]["base_market_value_usd"], 600.0)


if __name__ == "__main__":
    unittest.main()
