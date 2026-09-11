"""Market data fetching for the Investment Research Harness.

This module is the deterministic, external-data bridge that the harness itself
deliberately did not ship with: pulling quotes and FX observations over HTTP and
turning them into sourced ``QuoteObservation`` records that ``PortfolioStore``
can persist.

Design notes (pains learned from the first Agent-side implementation):

- Yahoo's chart API is used directly over HTTP instead of the ``yfinance``
  package, because ``yfinance`` pulls in numpy and breaks on common local
  Python environments (numpy binary mismatch with Python 3.12 on Windows).
- A-share symbols route to Tencent's quote endpoint; EastMoney is excluded
  because it is commonly blocked by local proxies (Clash etc.) while Tencent
  works on direct connection.
- FX direction trap: Yahoo's ``CNY=X`` quotes USDCNY (1 USD = X CNY). For a
  USD-base portfolio we must invert before persisting ``FX:CNY/USD``.

This module never touches the database. Persisting is done by callers
(``PortfolioService.refresh_quotes``) via ``PortfolioStore.record_quote``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from pydantic import BaseModel

DEFAULT_TIMEOUT_SECONDS = 15
USER_AGENT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={code}"

# DB symbol -> Tencent quote code. Tencent codes: sh/sz/bj prefix + 6-digit code.
TENCENT_A_SHARE_CODES = {
    "000975.SZ": "sz000975",
    "601899.SH": "sh601899",
}


class MarketDataError(RuntimeError):
    """Raised when a quote or FX observation cannot be fetched or parsed."""


class QuoteObservation(BaseModel):
    """A sourced price observation ready to persist via PortfolioStore."""

    symbol: str
    price: float
    currency: str
    as_of: datetime
    source: str
    source_ref: str | None = None


class RefreshReport(BaseModel):
    """Outcome of a portfolio-wide quote refresh."""

    observed: list[QuoteObservation]
    errors: list[str]
    as_of: datetime

    @property
    def success_count(self) -> int:
        return len(self.observed)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class MarketDataClient:
    """Thin HTTP client for quotes/FX. Stateless; safe to reuse."""

    timeout: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def _get(self, url: str) -> requests.Response:
        session = self.session or requests
        try:
            response = session.get(url, timeout=self.timeout, headers=USER_AGENT)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise MarketDataError(f"HTTP request failed for {url}: {exc}") from exc

    # ------------------------------------------------------------------
    # Public fetchers
    # ------------------------------------------------------------------

    def fetch_quote(self, symbol: str, *, as_of: datetime | None = None) -> QuoteObservation:
        """Fetch a price for a portfolio symbol, routing by suffix.

        A-share symbols (``.SZ``/``.SH``) go to Tencent; everything else
        (US equities, crypto, ETFs) goes to Yahoo.
        """
        upper = symbol.upper()
        as_of = as_of or datetime.now(timezone.utc)
        if upper in TENCENT_A_SHARE_CODES:
            return self._fetch_tencent(upper, as_of)
        if upper.endswith((".SZ", ".SH", ".BJ")):
            raise MarketDataError(f"{symbol}: A-share symbol has no configured Tencent code")
        return self._fetch_yahoo(upper, as_of)

    def fetch_fx(
        self,
        currency: str,
        *,
        base_currency: str = "USD",
        as_of: datetime | None = None,
    ) -> QuoteObservation:
        """Fetch ``FX:{currency}/{base_currency}``.

        Only a USD base is supported: Yahoo quotes ``CNY=X`` as USDCNY
        (1 USD = X CNY), so the value is inverted before being returned as
        ``price`` (amount of base currency per unit of ``currency``), which is
        exactly what ``PortfolioService._resolve_fx`` expects.
        """
        currency = currency.upper()
        base = base_currency.upper()
        if base != "USD":
            raise MarketDataError(f"fetch_fx currently supports only USD base, got {base}")
        if currency == base:
            raise ValueError("FX observation requires two different currencies")
        as_of = as_of or datetime.now(timezone.utc)
        # Yahoo symbol: "CNY=X" == USDCNY. Price returned is 1 USD in <currency>.
        usd_per_unit = self._fetch_yahoo_price(f"{currency}=X", as_of)
        return QuoteObservation(
            symbol=f"FX:{currency}/{base}",
            price=1.0 / usd_per_unit,
            currency=base,
            as_of=as_of,
            source="yahoo_chart",
            source_ref=f"yahoo_chart:{currency}=X",
        )

    def refresh_portfolio(
        self,
        symbols: list[str],
        *,
        fx_pairs: list[tuple[str, str]] | None = None,
        as_of: datetime | None = None,
    ) -> RefreshReport:
        """Fetch quotes for many symbols, isolating per-symbol failures."""
        as_of = as_of or datetime.now(timezone.utc)
        observed: list[QuoteObservation] = []
        errors: list[str] = []
        for symbol in symbols:
            if symbol.startswith("CASH_"):
                continue
            try:
                observed.append(self.fetch_quote(symbol, as_of=as_of))
            except Exception as exc:  # keep going on partial failures
                errors.append(f"{symbol}: {type(exc).__name__}: {exc}")
        for currency, base in fx_pairs or []:
            try:
                observed.append(self.fetch_fx(currency, base_currency=base, as_of=as_of))
            except Exception as exc:
                errors.append(f"FX:{currency}/{base}: {type(exc).__name__}: {exc}")
        return RefreshReport(observed=observed, errors=errors, as_of=as_of)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_yahoo(self, symbol: str, as_of: datetime) -> QuoteObservation:
        price = self._fetch_yahoo_price(symbol, as_of)
        return QuoteObservation(
            symbol=symbol,
            price=price,
            currency="USD",
            as_of=as_of,
            source="yahoo_chart",
            source_ref=f"yahoo_chart:{symbol}",
        )

    def _fetch_yahoo_price(self, symbol: str, as_of: datetime) -> float:
        response = self._get(YAHOO_CHART_URL.format(symbol=symbol))
        try:
            meta = response.json()["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise MarketDataError(f"cannot parse Yahoo response for {symbol}") from exc
        if price <= 0:
            raise MarketDataError(f"non-positive price for {symbol}: {price}")
        return price

    def _fetch_tencent(self, symbol: str, as_of: datetime) -> QuoteObservation:
        code = TENCENT_A_SHARE_CODES[symbol]
        response = self._get(TENCENT_QUOTE_URL.format(code=code))
        try:
            body = response.text
            start = body.find('="') + 2
            end = body.find('"', start)
            fields = body[start:end].split("~")
            price = float(fields[3])  # current price field
        except (ValueError, IndexError) as exc:
            raise MarketDataError(f"cannot parse Tencent response for {symbol}") from exc
        if price <= 0:
            raise MarketDataError(f"non-positive price for {symbol}: {price}")
        return QuoteObservation(
            symbol=symbol,
            price=price,
            currency="CNY",
            as_of=as_of,
            source="tencent_qt",
            source_ref=f"tencent_qt:{code}",
        )
