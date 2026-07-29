import math
import unittest
from unittest.mock import patch

from app.services import market_data


class _FakeIloc:
    def __getitem__(self, index):
        return math.nan


class _FakeCloseSeries:
    iloc = _FakeIloc()


class _FakeHistory:
    empty = False

    def __getitem__(self, column):
        assert column == "Close"
        return _FakeCloseSeries()


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period="5d"):
        return _FakeHistory()


class MarketDataNanGuardTests(unittest.TestCase):
    def test_cn_yfinance_fallback_ignores_nan_price(self):
        with patch.object(market_data.yf, "Ticker", _FakeTicker):
            price = market_data._get_cn_price_yfinance_fallback("000975.SZ")

        self.assertIsNone(price)

    def test_batch_prices_returns_none_when_jq_and_yfinance_prices_are_nan(self):
        with patch.object(market_data.jqdata_provider, "get_batch_prices", return_value={"000975.SZ": None}), \
             patch.object(market_data.yf, "Ticker", _FakeTicker):
            prices = market_data.get_batch_prices(["000975.SZ"])

        self.assertEqual(prices, {"000975.SZ": None})


if __name__ == "__main__":
    unittest.main()
