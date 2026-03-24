"""
Policy Engine — deterministic rule checks against investor profile.
No LLM involved.
"""
from __future__ import annotations

from app.models.domain import (
    InvestorProfile,
    PolicyResult,
    PolicyTrigger,
    Position,
    TriggerType,
)


def run_policy_check(positions: list[Position], profile: InvestorProfile) -> PolicyResult:
    triggers: list[PolicyTrigger] = []

    for p in positions:
        # Concentration check
        weight_decimal = p.weight / 100  # weight stored as percentage
        if weight_decimal > profile.max_position_weight:
            triggers.append(PolicyTrigger(
                trigger_type=TriggerType.concentration,
                symbol=p.symbol,
                current_value=round(p.weight, 1),
                threshold=round(profile.max_position_weight * 100, 1),
                message=(
                    f"{p.symbol} weight {p.weight:.1f}% exceeds your max "
                    f"{profile.max_position_weight*100:.0f}% limit."
                ),
            ))

        # Forbidden symbol check
        if p.symbol in profile.forbidden_symbols:
            triggers.append(PolicyTrigger(
                trigger_type=TriggerType.forbidden_asset,
                symbol=p.symbol,
                current_value=p.weight,
                threshold=0,
                message=f"{p.symbol} is in your forbidden list but currently held.",
            ))

    return PolicyResult(has_violations=len(triggers) > 0, triggers=triggers)
