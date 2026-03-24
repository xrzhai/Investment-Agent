"""CLI command: daily run"""
from __future__ import annotations

from datetime import date

import typer
from rich.console import Console
from rich.rule import Rule

app = typer.Typer(help="Run the full daily workflow.")
console = Console()


@app.command("run")
def run():
    """Run the full daily pipeline: refresh → snapshot → check → analyze → suggest."""
    from app.models.db import init_db
    from app.repositories.portfolio_repo import list_positions
    from app.cli.portfolio import _rows_to_positions, refresh, check
    from app.cli.analyze import analyze_portfolio, suggest
    from app.services.profile_service import load_profile

    init_db()
    console.rule(f"[bold]Daily Run — {date.today()}[/bold]")

    console.print("\n[bold cyan]Step 1/4: Refreshing prices …[/bold cyan]")
    refresh()

    console.print("\n[bold cyan]Step 2/4: Policy check …[/bold cyan]")
    check()

    console.print("\n[bold cyan]Step 3/4: Portfolio analysis …[/bold cyan]")
    analyze_portfolio()

    console.print("\n[bold cyan]Step 4/4: Suggestions …[/bold cyan]")
    suggest()

    console.rule("[bold]Daily Run Complete[/bold]")
