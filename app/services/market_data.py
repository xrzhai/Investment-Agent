"""
Market data service — unified entry point for all market data.
Routes A-share symbols (.SH/.SZ/.BJ) to JQData; everything else to yfinance.
"""
from __future__ import annotations

from typing import Optional

import yfinance as yf

from app.services import jqdata_provider


def _is_cn_a(symbol: str) -> bool:
    return symbol.endswith((".SH", ".SZ", ".BJ"))


def get_price(symbol: str) -> Optional[float]:
    """Return the latest closing price for a symbol, or None on failure."""
    # Special cases: non-exchange assets
    if symbol == "CASH":
        return 1.0
    if symbol == "CASH_CNY":
        return get_price("CNYUSD=X")  # CNY/USD exchange rate

    # A-share: route to JQData
    if _is_cn_a(symbol):
        price = jqdata_provider.get_price(symbol)
        if price is not None:
            return price
        # Fallback: try yfinance with .SS/.SZ format
        return _get_cn_price_yfinance_fallback(symbol)

    # US / crypto / FX: use yfinance
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
        if price:
            return float(price)
        # Fallback: last close from history
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _get_cn_price_yfinance_fallback(symbol: str) -> Optional[float]:
    """Try fetching A-share price via yfinance using .SS/.SZ suffix."""
    try:
        if symbol.endswith(".SH"):
            yf_sym = symbol[:-3] + ".SS"
        elif symbol.endswith(".SZ"):
            yf_sym = symbol  # yfinance uses .SZ directly
        else:
            return None
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def get_batch_prices(symbols: list[str]) -> dict[str, Optional[float]]:
    """Fetch prices for multiple symbols. Returns {symbol: price}."""
    cn_syms = [s for s in symbols if _is_cn_a(s)]
    other_syms = [s for s in symbols if not _is_cn_a(s)]

    results: dict[str, Optional[float]] = {}

    # Batch A-share prices via JQData
    if cn_syms:
        cn_prices = jqdata_provider.get_batch_prices(cn_syms)
        for sym, price in cn_prices.items():
            if price is None:
                price = _get_cn_price_yfinance_fallback(sym)
            results[sym] = price

    # Individual prices for other symbols (yfinance)
    for sym in other_syms:
        results[sym] = get_price(sym)

    return results


def get_fx_rate(from_currency: str = "CNY", to_currency: str = "USD") -> Optional[float]:
    """
    Get FX rate. Currently supports CNY→USD via yfinance CNYUSD=X.
    Returns None if unavailable.
    """
    if from_currency == to_currency:
        return 1.0
    if from_currency == "USD" and to_currency == "USD":
        return 1.0
    # CNY → USD
    if from_currency == "CNY" and to_currency == "USD":
        return get_price("CNYUSD=X")
    # USD → CNY (inverse)
    if from_currency == "USD" and to_currency == "CNY":
        rate = get_price("CNYUSD=X")
        return 1.0 / rate if rate else None
    return None


def get_news_summary(symbol: str, max_items: int = 5) -> str:
    """Return a text summary of recent news headlines for a symbol."""
    if _is_cn_a(symbol):
        return f"[A股] {symbol} — 市场上下文请通过 cn_market_data_tools.py 或 WebSearch 获取。"
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        if not news:
            return f"No recent news found for {symbol}."
        lines = []
        for item in news[:max_items]:
            content = item.get("content", item)
            title = content.get("title", "")
            provider = content.get("provider", {})
            publisher = provider.get("displayName", "") if isinstance(provider, dict) else ""
            if title:
                lines.append(f"- {title} ({publisher})")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch news for {symbol}: {e}"
