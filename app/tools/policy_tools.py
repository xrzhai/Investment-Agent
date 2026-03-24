"""
Policy Tools — standalone executable script for Claude Code.

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
        summary = "All positions pass policy checks."

    return {
        "timestamp": datetime.now().isoformat(),
        "has_violations": result.has_violations,
        "violation_count": violation_count,
        "triggers": triggers_data,
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
