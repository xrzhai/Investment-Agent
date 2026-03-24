#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch-write position metadata for all 9 covered symbols.
Bypasses argparse to avoid Windows CLI encoding issues with Chinese theme_tags.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.models.db import init_db
from app.repositories.portfolio_repo import list_positions, update_position_meta


def compute_cagr(target: float, current_price: float, horizon_months: int) -> float:
    if current_price <= 0 or horizon_months <= 0:
        return 0.0
    return (target / current_price) ** (12 / horizon_months) - 1


def write_meta(symbol, bear, base, bull, prob_bear, prob_base, prob_bull,
               horizon_months, sector, region, cap_style, growth_value,
               theme_tags, risk_level, ic_status, rows):
    row = rows.get(symbol)
    if row is None:
        print(f"[ERROR] {symbol} not found in portfolio")
        return False

    current_price = row.current_price
    if current_price <= 0:
        print(f"[WARN]  {symbol}: current_price=0, CAGR will be 0")

    cagr_bear = compute_cagr(bear, current_price, horizon_months)
    cagr_base = compute_cagr(base, current_price, horizon_months)
    cagr_bull = compute_cagr(bull, current_price, horizon_months)
    expected_cagr = (prob_bear * cagr_bear
                     + prob_base * cagr_base
                     + prob_bull * cagr_bull)

    theme_tags_json = json.dumps(theme_tags, ensure_ascii=False)

    meta = {
        "target_bear": bear,
        "target_base": base,
        "target_bull": bull,
        "prob_bear": prob_bear,
        "prob_base": prob_base,
        "prob_bull": prob_bull,
        "expected_cagr": expected_cagr,
        "time_horizon_months": horizon_months,
        "sector": sector,
        "region": region,
        "cap_style": cap_style,
        "growth_value": growth_value,
        "theme_tags": theme_tags_json,
        "risk_level": risk_level,
        "ic_status": ic_status,
    }

    result = update_position_meta(symbol, meta)
    if result:
        print(f"[OK]    {symbol:6s} | price={current_price:8.2f} | "
              f"bear={bear:6.0f} base={base:6.0f} bull={bull:6.0f} | "
              f"expected_cagr={expected_cagr*100:+.1f}%")
        return True
    else:
        print(f"[FAIL]  {symbol}")
        return False


# ---------------------------------------------------------------------------
# Extracted from thesis files — bear/base/bull targets, probabilities, meta
# ---------------------------------------------------------------------------
POSITIONS = [
    # ---- NVDA v4: Bear 15% / Base 40% / Bull 45% ----
    dict(
        symbol="NVDA",
        bear=98, base=198, bull=308,
        prob_bear=0.15, prob_base=0.40, prob_bull=0.45,
        horizon_months=18,
        sector="Technology", region="US", cap_style="mega", growth_value="growth",
        theme_tags=["AI基础设施", "CUDA生态", "数据中心", "GPU算力"],
        risk_level="high", ic_status="CLEAR",
    ),
    # ---- META v2: Bear 20% / Base 45% / Bull 35% ----
    dict(
        symbol="META",
        bear=392, base=700, bull=1050,
        prob_bear=0.20, prob_base=0.45, prob_bull=0.35,
        horizon_months=18,
        sector="Technology", region="US", cap_style="mega", growth_value="growth",
        theme_tags=["AI广告", "社交媒体", "数字广告"],
        risk_level="medium", ic_status="CLEAR",
    ),
    # ---- TSM v2: Bear 15% / Base 45% / Bull 40% ----
    dict(
        symbol="TSM",
        bear=224, base=360, bull=480,
        prob_bear=0.15, prob_base=0.45, prob_bull=0.40,
        horizon_months=18,
        sector="Technology", region="TW", cap_style="mega", growth_value="growth",
        theme_tags=["先进节点", "AI芯片代工", "半导体制造"],
        risk_level="high", ic_status="CLEAR",
    ),
    # ---- GOOGL v2: Bear 15% / Base 50% / Bull 35% ----
    dict(
        symbol="GOOGL",
        bear=160, base=336, bull=419,
        prob_bear=0.15, prob_base=0.50, prob_bull=0.35,
        horizon_months=18,
        sector="Technology", region="US", cap_style="mega", growth_value="growth",
        theme_tags=["搜索广告", "云计算", "AI整合"],
        risk_level="medium", ic_status="CLEAR",
    ),
    # ---- ALLW v1: Bear 25% / Base 50% / Bull 25% (ETF, risk-parity hedge) ----
    dict(
        symbol="ALLW",
        bear=22, base=32, bull=36,
        prob_bear=0.25, prob_base=0.50, prob_bull=0.25,
        horizon_months=15,
        sector="Multi-Asset", region="Global", cap_style="etf", growth_value="value",
        theme_tags=["风险平价", "宏观对冲", "多资产"],
        risk_level="medium", ic_status="CLEAR",
    ),
    # ---- BMNR v1: Bear(Adverse) 45% / Base 35% / Bull 20% ----
    dict(
        symbol="BMNR",
        bear=8, base=34, bull=75,
        prob_bear=0.45, prob_base=0.35, prob_bull=0.20,
        horizon_months=18,
        sector="Crypto", region="US", cap_style="small", growth_value="growth",
        theme_tags=["以太坊财库", "加密质押", "MAVAN"],
        risk_level="high", ic_status="CLEAR",
    ),
    # ---- MSFT v1: Bear 25% / Base 45% / Bull 30% ----
    dict(
        symbol="MSFT",
        bear=320, base=435, bull=500,
        prob_bear=0.25, prob_base=0.45, prob_bull=0.30,
        horizon_months=15,
        sector="Technology", region="US", cap_style="mega", growth_value="growth",
        theme_tags=["Azure云", "AI工作负载", "Copilot"],
        risk_level="medium", ic_status="CLEAR",
    ),
    # ---- NFLX v1: Bear 25% / Base 55% / Bull 20% ----
    dict(
        symbol="NFLX",
        bear=75, base=105, bull=125,
        prob_bear=0.25, prob_base=0.55, prob_bull=0.20,
        horizon_months=15,
        sector="Communication Services", region="US", cap_style="large", growth_value="growth",
        theme_tags=["流媒体", "广告变现", "直播内容"],
        risk_level="medium", ic_status="CLEAR",
    ),
    # ---- PDD v1: Bear 35% / Base 45% / Bull 20% ----
    dict(
        symbol="PDD",
        bear=68, base=130, bull=160,
        prob_bear=0.35, prob_base=0.45, prob_bull=0.20,
        horizon_months=15,
        sector="Consumer Discretionary", region="CN", cap_style="large", growth_value="value",
        theme_tags=["中国电商", "Temu跨境", "拼多多"],
        risk_level="high", ic_status="CLEAR",
    ),
]


def main():
    print("Initialising DB...")
    init_db()
    rows = {r.symbol: r for r in list_positions()}
    print(f"Found {len(rows)} positions in portfolio: {sorted(rows.keys())}\n")

    ok = 0
    for pos in POSITIONS:
        success = write_meta(**pos, rows=rows)
        if success:
            ok += 1

    print(f"\n{'='*60}")
    print(f"Written {ok}/{len(POSITIONS)} positions successfully.")


if __name__ == "__main__":
    main()
