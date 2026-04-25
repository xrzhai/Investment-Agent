"""
Policy Tools — standalone executable script for agent workflows.

Usage:
    python app/tools/policy_tools.py

Outputs JSON to stdout: policy check results against investor profile.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engines.policy_engine import run_policy_check
from app.engines.portfolio_engine import compute_positions
from app.repositories.options_repo import compute_open_put_exposure, list_option_contracts
from app.repositories.portfolio_repo import list_positions
from app.services.profile_service import load_profile


def get_policy_check() -> dict:
    """
    Run policy checks against current portfolio and investor profile.
    Returns structured result dict.
    """
    rows = list_positions()
    profile = load_profile()

    if not rows:
        return {
            "timestamp": datetime.now().isoformat(),
            "has_violations": False,
            "violation_count": 0,
            "triggers": [],
            "summary": "No positions to check.",
        }

    positions = compute_positions(rows)
    result = run_policy_check(positions, profile)
    option_signals = []

    open_option_rows = list_option_contracts(status="open")
    if open_option_rows:
        total_value_usd = round(sum(p.base_market_value for p in positions), 2)
        options_exposure = compute_open_put_exposure(
            spot_positions=positions,
            option_rows=open_option_rows,
            total_portfolio_value_usd=total_value_usd,
            fetch_spot_prices=True,
        )
        for contract in options_exposure["contracts"]:
            assigned_weight = contract.get("assigned_weight_estimate_pct")
            if assigned_weight is not None and (assigned_weight / 100) > profile.max_position_weight:
                triggers_data_message = (
                    f"{contract['underlying_symbol']} fully-assigned weight ~{assigned_weight:.1f}% exceeds your max "
                    f"{profile.max_position_weight*100:.0f}% limit."
                )
                option_signals.append({
                    "type": "contingent_exposure",
                    "symbol": contract["underlying_symbol"],
                    "current_value": assigned_weight,
                    "threshold": round(profile.max_position_weight * 100, 1),
                    "message": triggers_data_message,
                    "severity": "warning",
                })
        for currency, gap in options_exposure["totals"]["cash_gap_vs_reserved_by_currency"].items():
            if gap < 0:
                option_signals.append({
                    "type": "liquidity",
                    "symbol": currency,
                    "current_value": gap,
                    "threshold": 0.0,
                    "message": (
                        f"{currency} cash gap vs reserved sold-put exposure = {gap:.2f}. "
                        "Treat this as a liquidity-planning signal, not an automatic hard fail."
                    ),
                    "severity": "info",
                })
    else:
        options_exposure = None

    triggers_data = []
    for t in result.triggers:
        triggers_data.append({
            "type": t.trigger_type.value,
            "symbol": t.symbol,
            "current_value": t.current_value,
            "threshold": t.threshold,
            "message": t.message,
        })

    violation_count = len(result.triggers)

    # Build a plain-text summary for quick reading
    if result.has_violations:
        summary = f"{violation_count} violation(s) found: " + "; ".join(
            t.message for t in result.triggers
        )
    else:
        summary = "All spot positions pass policy checks."
    if option_signals:
        summary += " Option signals: " + "; ".join(s["message"] for s in option_signals)

    return {
        "timestamp": datetime.now().isoformat(),
        "has_violations": result.has_violations,
        "violation_count": violation_count,
        "triggers": triggers_data,
        "option_signals": option_signals,
        "options_exposure": options_exposure,
        "profile_rules": {
            "max_position_weight_pct": round(profile.max_position_weight * 100, 1),
            "max_drawdown_tolerance_pct": round(profile.max_drawdown_tolerance * 100, 1),
            "forbidden_symbols": list(profile.forbidden_symbols),
        },
        "summary": summary,
    }


if __name__ == "__main__":
    result = get_policy_check()
    print(json.dumps(result, indent=2, ensure_ascii=False))
