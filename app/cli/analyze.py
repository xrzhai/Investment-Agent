"""CLI commands: analyze *  |  suggest *"""
from __future__ import annotations

import typer
from rich.console import Console

from app.models.db import init_db

app = typer.Typer(help="Analyze portfolio and assets; generate suggestions.")
console = Console()


@app.command("portfolio")
def analyze_portfolio():
    """Explain today's portfolio state using LLM."""
    init_db()
    from app.engines.recommendation_engine import explain_portfolio
    from app.repositories.portfolio_repo import list_positions
    from app.cli.portfolio import _rows_to_positions
    from app.services.profile_service import load_profile

    rows = list_positions()
    if not rows:
        console.print("[yellow]No positions.[/yellow]")
        return

    positions = _rows_to_positions(rows)
    profile = load_profile()
    explanation = explain_portfolio(positions, profile)
    console.rule("Portfolio Analysis")
    console.print(explanation)


@app.command("asset")
def analyze_asset(symbol: str = typer.Argument(..., help="Ticker symbol")):
    """Analyze a specific asset using recent news and price data."""
    init_db()
    from app.engines.recommendation_engine import explain_asset
    symbol = symbol.upper()
    result = explain_asset(symbol)
    console.rule(f"Asset Analysis: {symbol}")
    console.print(result)


@app.command("suggest")
def suggest():
    """Generate action suggestions based on current portfolio state and policy."""
    init_db()
    from app.engines.recommendation_engine import generate_suggestions
    from app.repositories.portfolio_repo import list_positions
    from app.cli.portfolio import _rows_to_positions
    from app.services.profile_service import load_profile

    rows = list_positions()
    if not rows:
        console.print("[yellow]No positions.[/yellow]")
        return

    positions = _rows_to_positions(rows)
    profile = load_profile()

    from app.models.domain import Recommendation
    from app.repositories.journal_repo import save_recommendation

    console.print("Generating suggestions …")
    suggestions = generate_suggestions(positions, profile)
    console.rule("Suggestions")
    for draft, text in suggestions:
        label = f"[{draft.scope}] {draft.suggested_action.value.replace('_', ' ').upper()}"
        console.print(label)
        console.print(text)
        console.print()
        rec = Recommendation(
            scope=draft.scope,
            action=draft.suggested_action,
            reason=text,
            evidence=draft.evidence_points,
            risk_notes=draft.risk_notes,
            confidence=draft.confidence,
        )
        save_recommendation(rec)
