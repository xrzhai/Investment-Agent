"""
Recommendation Engine — combines portfolio state + policy results,
builds a structured RecommendationDraft, then uses LLM to verbalize.
"""
from __future__ import annotations

from app.models.domain import (
    ActionType,
    InvestorProfile,
    PolicyTrigger,
    Position,
    RecommendationDraft,
    TriggerType,
)
from app.engines.policy_engine import run_policy_check


def _build_drafts(
    positions: list[Position],
    profile: InvestorProfile,
) -> list[RecommendationDraft]:
    policy_result = run_policy_check(positions, profile)
    drafts: list[RecommendationDraft] = []

    if not policy_result.has_violations:
        drafts.append(RecommendationDraft(
            scope="portfolio",
            trigger_type=TriggerType.thesis_drift,
            suggested_action=ActionType.hold,
            rationale_points=["All policy checks passed."],
            evidence_points=[f"{len(positions)} positions within defined limits."],
            risk_notes=["Continue monitoring for changes."],
            confidence=0.8,
        ))
        return drafts

    for trigger in policy_result.triggers:
        if trigger.trigger_type == TriggerType.concentration:
            drafts.append(RecommendationDraft(
                scope=trigger.symbol or "portfolio",
                trigger_type=TriggerType.concentration,
                suggested_action=ActionType.consider_trim,
                rationale_points=[trigger.message],
                evidence_points=[
                    f"Current weight: {trigger.current_value:.1f}%",
                    f"Max allowed: {trigger.threshold:.1f}%",
                ],
                risk_notes=["Trimming may trigger capital gains taxes."],
                confidence=0.75,
            ))
        elif trigger.trigger_type == TriggerType.forbidden_asset:
            drafts.append(RecommendationDraft(
                scope=trigger.symbol or "portfolio",
                trigger_type=TriggerType.forbidden_asset,
                suggested_action=ActionType.research,
                rationale_points=[trigger.message],
                evidence_points=["Position exists but violates your own rules."],
                risk_notes=["Review if your rule should be updated, or exit the position."],
                confidence=0.9,
            ))

    return drafts


def _draft_to_prompt(draft: RecommendationDraft, profile: InvestorProfile) -> str:
    from app.services.coverage_service import load_thesis
    from app.services.principles_service import load_principles

    rationale = "\n".join(f"- {p}" for p in draft.rationale_points)
    evidence = "\n".join(f"- {p}" for p in draft.evidence_points)
    risks = "\n".join(f"- {p}" for p in draft.risk_notes)

    coverage_section = ""
    if draft.scope != "portfolio":
        thesis = load_thesis(draft.scope)
        if thesis:
            # Extract the Invalidation Conditions and position management sections
            # to keep the prompt focused — full thesis can be very long
            lines = thesis.splitlines()
            sections: dict[str, list[str]] = {}
            current: str | None = None
            for line in lines:
                if line.startswith("## 错误指标") or line.startswith("## 头寸管理"):
                    current = line.strip()
                    sections[current] = []
                elif line.startswith("## ") and current:
                    current = None
                elif current is not None:
                    sections[current].append(line)
            excerpts = []
            for heading, body in sections.items():
                block = "\n".join(body).strip()
                if block:
                    excerpts.append(f"{heading}\n{block}")
            if excerpts:
                coverage_section = (
                    "\n\nCoverage Thesis Context (use this to ground your recommendation):\n"
                    + "\n\n".join(excerpts)
                )

    principles = load_principles()
    principles_section = ""
    if principles:
        principles_section = (
            "\n\nUser's Investment Principles (use these to evaluate alignment and flag any conflicts):\n"
            + principles
        )

    return f"""You are a disciplined investment copilot. The user's style is "{profile.style}",
time horizon is "{profile.time_horizon}", risk tolerance is "{profile.risk_tolerance}".

Based on the following structured analysis, write a clear, concise recommendation (3-5 sentences).
Include: what triggered this, the suggested action, and what uncertainty remains.
Do NOT use jargon. Do NOT make price forecasts.

Scope: {draft.scope}
Trigger: {draft.trigger_type.value}
Suggested action: {draft.suggested_action.value.replace('_', ' ')}
Confidence: {draft.confidence:.0%}

Rationale:
{rationale}

Evidence:
{evidence}

Risk notes:
{risks}{coverage_section}{principles_section}

Write the recommendation now:"""


def generate_suggestions(
    positions: list[Position], profile: InvestorProfile
) -> list[tuple[RecommendationDraft, str]]:
    from app.services.llm_client import call_llm

    drafts = _build_drafts(positions, profile)
    results = []
    for draft in drafts:
        prompt = _draft_to_prompt(draft, profile)
        text = call_llm(prompt)
        results.append((draft, text))
    return results


def explain_portfolio(positions: list[Position], profile: InvestorProfile) -> str:
    from app.services.llm_client import call_llm

    total = sum(p.market_value for p in positions)
    top = sorted(positions, key=lambda x: -x.weight)[:5]
    lines = [f"  {p.symbol}: {p.weight:.1f}%" for p in top]
    portfolio_summary = "\n".join(lines)

    prompt = f"""You are a disciplined investment copilot. Summarize the current portfolio state
in 3-4 sentences. Focus on: composition and concentration.
Be factual. Do not forecast.

Total portfolio value: ${total:,.2f}
Investor style: {profile.style}, horizon: {profile.time_horizon}

Top holdings:
{portfolio_summary}

Write the summary now:"""
    return call_llm(prompt)


def explain_asset(symbol: str) -> str:
    from app.services.llm_client import call_llm
    from app.services.market_data import get_news_summary
    from app.services.coverage_service import load_thesis
    from app.repositories.journal_repo import list_journal_entries

    news = get_news_summary(symbol)
    thesis = load_thesis(symbol)

    # Pull up to 3 recent research notes from the journal
    recent_notes = list_journal_entries(scope=symbol, limit=3)
    notes_text = ""
    if recent_notes:
        formatted = []
        for n in recent_notes:
            date = n.timestamp.strftime("%Y-%m-%d")
            tag = n.user_note or ""
            content = n.agent_note or n.thesis or ""
            if content:
                formatted.append(f"[{date}] {tag} {content}".strip())
        if formatted:
            notes_text = "\n\nRecent research notes:\n" + "\n".join(formatted)

    if thesis:
        prompt = f"""You are a disciplined investment copilot analyzing {symbol}.

Coverage Thesis:
{thesis}

Recent news:
{news}{notes_text}

Based on the thesis and recent news, assess:
1. Is the Base Scenario still intact, or is the Adverse Scenario becoming more likely?
2. Check each Invalidation Condition — is it TRIGGERED, WATCHING, or CLEAR?
3. Has the Risk/Return profile shifted meaningfully?

Write a focused 3-5 sentence analysis. Do not forecast prices. Flag any Invalidation Condition \
that appears close to triggering. If no thesis exists for the next symbol, note it.

Write the analysis now:"""
    else:
        prompt = f"""You are a disciplined investment copilot. Based on recent news for {symbol},
explain what happened and whether it is likely noise or a meaningful development (2-3 sentences).
Do not forecast price. Note uncertainty.

Recent news summary:
{news}{notes_text}

Write the analysis now:

(Note: No coverage thesis found for {symbol} — consider initiating coverage.)"""

    return call_llm(prompt)
