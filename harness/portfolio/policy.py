from __future__ import annotations

from harness.portfolio.models import InvestorProfile, PolicyReport, PolicySignal, PortfolioState
from harness.portfolio.options import compute_open_put_exposure


def evaluate_policy(state: PortfolioState, profile: InvestorProfile) -> PolicyReport:
    """Evaluate portfolio guardrails; signals never execute a trade."""

    signals: list[PolicySignal] = []
    warnings = list(state.warnings)
    forbidden = {symbol.upper() for symbol in profile.forbidden_symbols}

    for position in state.positions:
        if position.symbol.startswith("CASH_"):
            continue
        if position.symbol in forbidden and position.quantity:
            signals.append(
                PolicySignal(
                    signal_type="forbidden_symbol",
                    severity="violation",
                    symbol=position.symbol,
                    message=f"{position.symbol} is forbidden by the investor profile",
                )
            )
        if position.weight_pct is not None:
            weight = position.weight_pct / 100
            if weight > profile.max_position_weight:
                signals.append(
                    PolicySignal(
                        signal_type="position_concentration",
                        severity="violation",
                        symbol=position.symbol,
                        current_value=weight,
                        threshold=profile.max_position_weight,
                        message=f"{position.symbol} weight {weight:.1%} exceeds the {profile.max_position_weight:.1%} limit",
                    )
                )

    if state.cash_pct is None:
        warnings.append("cash policy could not be evaluated because portfolio total is zero")
    elif state.cash_pct / 100 < profile.min_cash_pct:
        signals.append(
            PolicySignal(
                signal_type="minimum_cash",
                severity="violation",
                current_value=state.cash_pct / 100,
                threshold=profile.min_cash_pct,
                message=f"cash {state.cash_pct / 100:.1%} is below the {profile.min_cash_pct:.1%} minimum",
            )
        )

    exposure = compute_open_put_exposure(
        positions=state.positions,
        option_contracts=state.open_options,
        portfolio_total_value=state.total_value,
    )
    for currency, gap in exposure["cash_gap_by_currency"].items():
        if gap < 0:
            signals.append(
                PolicySignal(
                    signal_type="option_cash_coverage",
                    severity="violation",
                    current_value=gap,
                    threshold=0.0,
                    message=f"open short puts exceed available {currency} cash by {abs(gap):,.2f}",
                )
            )
    for contract in exposure["contracts"]:
        assigned_weight = contract["assigned_weight_estimate_pct"]
        if assigned_weight is not None and assigned_weight / 100 > profile.max_position_weight:
            signals.append(
                PolicySignal(
                    signal_type="post_assignment_concentration",
                    severity="warning",
                    symbol=contract["underlying_symbol"],
                    current_value=assigned_weight / 100,
                    threshold=profile.max_position_weight,
                    message=(
                        f"option assignment could raise {contract['underlying_symbol']} to "
                        f"{assigned_weight:.1f}% of the portfolio"
                    ),
                )
            )

    return PolicyReport(as_of=state.as_of, signals=signals, warnings=warnings)
