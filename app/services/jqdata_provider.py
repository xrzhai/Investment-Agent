"""
JQData (聚宽) provider — A-share market data.

Authentication uses env vars JQ_USER and JQ_PASS.
All public functions accept canonical symbols (.SH/.SZ/.BJ) and handle
the mapping to JQData format (.XSHG/.XSHE/.XBEI) internally.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Optional

_authenticated = False


# ---------------------------------------------------------------------------
# Symbol mapping
# ---------------------------------------------------------------------------

def to_jq_symbol(symbol: str) -> str:
    """
    Convert canonical A-share symbol to JQData format.
      600519.SH  → 600519.XSHG
      000001.SZ  → 000001.XSHE
      430047.BJ  → 430047.XBEI
    """
    if symbol.endswith(".SH"):
        return symbol[:-3] + ".XSHG"
    if symbol.endswith(".SZ"):
        return symbol[:-3] + ".XSHE"
    if symbol.endswith(".BJ"):
        return symbol[:-3] + ".XBEI"
    return symbol  # pass through if already in JQ format or unknown


def from_jq_symbol(jq_symbol: str) -> str:
    """Convert JQData symbol back to canonical format."""
    if jq_symbol.endswith(".XSHG"):
        return jq_symbol[:-5] + ".SH"
    if jq_symbol.endswith(".XSHE"):
        return jq_symbol[:-5] + ".SZ"
    if jq_symbol.endswith(".XBEI"):
        return jq_symbol[:-5] + ".BJ"
    return jq_symbol


def is_cn_a_symbol(symbol: str) -> bool:
    return symbol.endswith((".SH", ".SZ", ".BJ"))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _ensure_auth() -> bool:
    """Authenticate with JQData using env vars. Returns True if successful."""
    global _authenticated
    if _authenticated:
        return True
    user = os.environ.get("JQ_USER", "")
    password = os.environ.get("JQ_PASS", "")
    if not user or not password:
        return False
    try:
        import jqdatasdk as jq
        jq.auth(user, password)
        _authenticated = True
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Price data
# ---------------------------------------------------------------------------

def get_price(symbol: str) -> Optional[float]:
    """
    Get latest price for a canonical A-share symbol (e.g. '600519.SH').
    Returns None on failure.
    """
    if not _ensure_auth():
        return None
    try:
        import jqdatasdk as jq
        jq_sym = to_jq_symbol(symbol)
        # get_price returns a DataFrame; fetch last 2 trading days and take latest close
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        df = jq.get_price(jq_sym, start_date=start, end_date=end, frequency="daily",
                          fields=["close"], skip_paused=True)
        if df is not None and not df.empty:
            return float(df["close"].iloc[-1])
    except Exception:
        pass
    return None


def get_batch_prices(symbols: list[str]) -> dict[str, Optional[float]]:
    """
    Get latest prices for multiple canonical A-share symbols.
    Returns {symbol: price}.
    """
    results: dict[str, Optional[float]] = {}
    if not _ensure_auth():
        return {s: None for s in symbols}
    try:
        import jqdatasdk as jq
        jq_syms = [to_jq_symbol(s) for s in symbols]
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        df = jq.get_price(jq_syms, start_date=start, end_date=end, frequency="daily",
                          fields=["close"], skip_paused=True, panel=False)
        if df is not None and not df.empty:
            # df has columns: time, code, close
            latest = df.groupby("code")["close"].last()
            for orig, jq_sym in zip(symbols, jq_syms):
                results[orig] = float(latest[jq_sym]) if jq_sym in latest else None
            return results
    except Exception:
        pass
    return {s: None for s in symbols}


def get_price_history(symbol: str, start: str, end: str,
                      adjust: str = "pre") -> Optional[object]:
    """
    Get price history DataFrame for a canonical A-share symbol.
    adjust: 'pre' (前复权) | 'post' (后复权) | None (不复权)
    Returns pandas DataFrame with columns [open, close, high, low, volume] or None.
    """
    if not _ensure_auth():
        return None
    try:
        import jqdatasdk as jq
        jq_sym = to_jq_symbol(symbol)
        df = jq.get_price(jq_sym, start_date=start, end_date=end, frequency="daily",
                          fields=["open", "close", "high", "low", "volume"],
                          skip_paused=True, fq=adjust)
        return df
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fundamental data
# ---------------------------------------------------------------------------

def get_fundamentals(symbol: str) -> dict:
    """
    Get key fundamental metrics for a canonical A-share symbol.
    Returns a dict with available fields; missing fields are omitted.

    Note: financial indicator fields (EPS, ROE, etc.) use statDate to fetch
    the latest completed fiscal year's full-year data, not single-quarter data.
    """
    if not _ensure_auth():
        return {}
    try:
        import jqdatasdk as jq
        from jqdatasdk import query, valuation, indicator

        jq_sym = to_jq_symbol(symbol)
        today = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year

        # Valuation metrics — real-time, use date=today
        q = query(valuation).filter(valuation.code == jq_sym)
        val_df = jq.get_fundamentals(q, date=today)

        result: dict = {}
        if val_df is not None and not val_df.empty:
            row = val_df.iloc[0]
            for field in ["pe_ratio", "pb_ratio", "ps_ratio", "pcf_ratio",
                          "market_cap", "circulating_market_cap", "turnover_ratio",
                          "pe_ratio_lyr"]:
                val = row.get(field)
                if val is not None and str(val) not in ("nan", "None", "inf"):
                    result[field] = float(val)

        # Financial indicators — use statDate to get full fiscal-year data.
        # Using date=today returns single-quarter incremental EPS/ROE, not annual.
        # Try the most recently completed fiscal year first (current_year - 1),
        # then fall back to current_year if annual report already published (>= May).
        annual_year = current_year - 1
        q2 = query(indicator).filter(indicator.code == jq_sym)
        ind_df = jq.get_fundamentals(q2, statDate=str(annual_year))
        if (ind_df is None or ind_df.empty) and datetime.now().month >= 5:
            ind_df = jq.get_fundamentals(q2, statDate=str(current_year))
            if ind_df is not None and not ind_df.empty:
                annual_year = current_year

        if ind_df is not None and not ind_df.empty:
            row2 = ind_df.iloc[0]
            result["financials_period"] = f"FY{annual_year}"
            for field in ["roe", "roa", "gross_profit_margin", "net_profit_margin",
                          "eps", "inc_total_revenue_year_on_year",
                          "inc_net_profit_to_shareholders_year_on_year"]:
                val = row2.get(field)
                if val is not None and str(val) not in ("nan", "None", "inf"):
                    result[field] = round(float(val), 4)

        return result
    except Exception:
        return {}


def get_consensus_estimates(symbol: str) -> dict:
    """
    Get analyst consensus EPS and net profit forecasts via AkShare (同花顺).
    Returns forward EPS estimates for FY+1, FY+2, FY+3 and derived forward P/E.

    Source: 同花顺 stock_profit_forecast_ths, indicator='预测年报每股收益'
    """
    try:
        import akshare as ak
        bare = symbol.split(".")[0]  # strip exchange suffix for AkShare

        eps_df = ak.stock_profit_forecast_ths(symbol=bare, indicator="预测年报每股收益")
        np_df = ak.stock_profit_forecast_ths(symbol=bare, indicator="预测年报净利润")

        if eps_df is None or eps_df.empty:
            return {}

        # Column order: 年份, 预测机构数, 最小值, 均值, 最大值, 行业平均值
        eps_df.columns = ["year", "num_analysts", "eps_min", "eps_avg", "eps_max", "industry_avg_eps"]

        result: dict = {"source": "ths", "estimates": []}
        for _, row in eps_df.iterrows():
            entry: dict = {
                "year": int(row["year"]),
                "num_analysts": int(row["num_analysts"]),
                "eps_avg": float(row["eps_avg"]),
                "eps_min": float(row["eps_min"]),
                "eps_max": float(row["eps_max"]),
            }
            # Attach net profit consensus if available
            if np_df is not None and not np_df.empty:
                np_df.columns = ["year", "num_analysts", "np_min", "np_avg", "np_max", "industry_avg_np"]
                np_row = np_df[np_df["year"] == row["year"]]
                if not np_row.empty:
                    entry["net_profit_avg_cny_bn"] = float(np_row.iloc[0]["np_avg"])
            result["estimates"].append(entry)

        return result
    except Exception:
        return {}


def get_security_info(symbol: str) -> dict:
    """
    Get basic security info (name, type, listed date etc.) for a canonical symbol.
    """
    if not _ensure_auth():
        return {}
    try:
        import jqdatasdk as jq
        jq_sym = to_jq_symbol(symbol)
        info = jq.get_security_info(jq_sym)
        if info is None:
            return {}
        return {
            "name": getattr(info, "display_name", "") or getattr(info, "name", ""),
            "type": getattr(info, "type", ""),
            "start_date": str(getattr(info, "start_date", "")),
            "end_date": str(getattr(info, "end_date", "")),
            "exchange": getattr(info, "exchange", ""),
        }
    except Exception:
        return {}
