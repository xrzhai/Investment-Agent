"""CLI commands: profile *"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from app.services.profile_service import load_profile, save_profile
from app.models.domain import InvestorProfile

app = typer.Typer(help="Manage your investor profile and philosophy.")
console = Console()


@app.command("show")
def show():
    """Display your current investor profile."""
    profile = load_profile()
    table = Table(title="Investor Profile", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Style", profile.style)
    table.add_row("Time Horizon", profile.time_horizon)
    table.add_row("Risk Tolerance", profile.risk_tolerance)
    table.add_row("Max Position Weight", f"{profile.max_position_weight*100:.0f}%")
    table.add_row("Max Drawdown Tolerance", f"{profile.max_drawdown_tolerance*100:.0f}%")
    table.add_row("Min Cash %", f"{profile.min_cash_pct*100:.0f}%")
    table.add_row("Forbidden Symbols", ", ".join(profile.forbidden_symbols) or "none")
    table.add_row("Notes", profile.notes or "-")
    console.print(table)


@app.command("init")
def init():
    """Interactively initialize your investor profile."""
    console.print("[bold]Setting up your investor profile[/bold]\n")

    style = typer.prompt("Investment style (growth/value/blend)", default="growth")
    horizon = typer.prompt("Time horizon (short/medium/long)", default="long")
    risk = typer.prompt("Risk tolerance (low/medium/high)", default="medium")
    max_weight = typer.prompt("Max single position weight % (e.g. 20)", default="20")
    max_dd = typer.prompt("Max drawdown tolerance % (e.g. 15)", default="15")
    min_cash = typer.prompt("Min cash % (e.g. 5)", default="5")
    forbidden = typer.prompt("Forbidden symbols, comma-separated (leave blank for none)", default="")
    notes = typer.prompt("Notes (optional)", default="")

    profile = InvestorProfile(
        style=style,
        time_horizon=horizon,
        risk_tolerance=risk,
        max_position_weight=float(max_weight) / 100,
        max_drawdown_tolerance=float(max_dd) / 100,
        min_cash_pct=float(min_cash) / 100,
        forbidden_symbols=[s.strip().upper() for s in forbidden.split(",") if s.strip()],
        notes=notes,
    )
    save_profile(profile)
    console.print("[green]OK[/green] Profile saved.")


@app.command("update")
def update(
    field: str = typer.Argument(..., help="Field name to update"),
    value: str = typer.Argument(..., help="New value"),
):
    """Update a single profile field. E.g.: profile update max_position_weight 0.25"""
    profile = load_profile()
    data = profile.model_dump()
    if field not in data:
        console.print(f"[red]Unknown field: {field}[/red]")
        console.print(f"Valid fields: {', '.join(data.keys())}")
        raise typer.Exit(1)

    original = data[field]
    # Type-coerce based on original type
    if isinstance(original, float):
        data[field] = float(value)
    elif isinstance(original, int):
        data[field] = int(value)
    elif isinstance(original, list):
        data[field] = [v.strip().upper() for v in value.split(",") if v.strip()]
    else:
        data[field] = value

    save_profile(InvestorProfile.model_validate(data))
    console.print(f"[green]OK[/green] {field} updated: {original} -> {data[field]}")
