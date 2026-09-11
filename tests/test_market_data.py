from __future__ import annotations

from datetime import datetime, timezone

import pytest

from harness.portfolio.market_data import MarketDataClient, MarketDataError, QuoteObservation, RefreshReport


class FakeResponse:
    def __init__(self, text: str = "", json_data=None, status_code: int = 200):
        self._text = text
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    @property
    def text(self) -> str:
        return self._text

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, timeout=None, headers=None) -> FakeResponse:
        self.calls.append(url)
        for needle, resp in self.responses.items():
            if needle in url:
                return resp
        raise MarketDataError(f"no fake response for {url}")


def make_yahoo_response(price: float) -> FakeResponse:
    return FakeResponse(json_data={"chart": {"result": [{"meta": {"regularMarketPrice": price}}]}})


def make_tencent_response(price: float) -> FakeResponse:
    return FakeResponse(text=f'v_sh600519="1~name~600519~{price}~0~0~0"')


def test_yahoo_symbol_route_and_parse():
    client = MarketDataClient(session=FakeSession({"NVDA": make_yahoo_response(206.5)}))
    obs = client.fetch_quote("NVDA", as_of=datetime(2026, 8, 3, tzinfo=timezone.utc))
    assert isinstance(obs, QuoteObservation)
    assert obs.price == 206.5
    assert obs.currency == "USD"
    assert obs.source == "yahoo_chart"


def test_tencent_symbol_route_and_parse():
    client = MarketDataClient(session=FakeSession({"sz000975": make_tencent_response(22.83)}))
    obs = client.fetch_quote("000975.SZ", as_of=datetime(2026, 8, 3, tzinfo=timezone.utc))
    assert obs.price == 22.83
    assert obs.currency == "CNY"
    assert obs.source == "tencent_qt"


def test_fx_inverts_usdcny_direction():
    # Yahoo "CNY=X" returns 1 USD = 6.7445 CNY; harness must store 1 CNY = 0.1483 USD.
    client = MarketDataClient(session=FakeSession({"CNY=X": make_yahoo_response(6.7445)}))
    obs = client.fetch_fx("CNY", as_of=datetime(2026, 8, 3, tzinfo=timezone.utc))
    assert obs.symbol == "FX:CNY/USD"
    assert obs.price == pytest.approx(0.14827, abs=1e-4)
    assert obs.currency == "USD"


def test_fx_rejects_non_usd_base():
    client = MarketDataClient()
    with pytest.raises(MarketDataError):
        client.fetch_fx("CNY", base_currency="EUR")


def test_refresh_portfolio_isolates_partial_failures():
    session = FakeSession(
        {
            "NVDA": make_yahoo_response(206.5),
            "CNY=X": make_yahoo_response(6.7445),
        }
    )
    client = MarketDataClient(session=session)
    report = client.refresh_portfolio(
        ["NVDA", "GOOGL", "000975.SZ", "CASH_USD"],
        fx_pairs=[("CNY", "USD")],
        as_of=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )
    assert isinstance(report, RefreshReport)
    assert report.success_count == 2  # NVDA + FX; GOOGL fails (no fake), CASH skipped
    assert report.ok is False
    assert any("GOOGL" in e for e in report.errors)


def test_malformed_yahoo_response_raises_market_data_error():
    client = MarketDataClient(session=FakeSession({"NVDA": FakeResponse(json_data={"bad": "shape"})}))
    with pytest.raises(MarketDataError):
        client.fetch_quote("NVDA")
