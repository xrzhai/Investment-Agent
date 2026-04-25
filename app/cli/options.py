"""CLI commands: options *"""
from __future__ import annotations

import json
from datetime import date

import typer
from rich.console import Console
from rich.table import Table

from app.models.db import init_db
from app.repositories.options_repo import (
    create_option_contract,
    list_option_contracts,
    mark_option_assigned,
    mark_option_closed,
    mark_option_expired,
)
from app.tools.option_tools import get_option_summary

app = typer.Typer(help="Manage sold puts and contingent exposure.")
console = Console()


@app.command("open-put")
def open_put(
    symbol: str = typer.Argument(..., help="Underlying symbol, e.g. BMNR"),
    expiry: str = typer.Argument(..., help="Expiry date in YYYY-MM-DD"),
    strike: float = typer.Argument(..., help="Strike price"),
    contracts: int = typer.Argument(..., help="Short contracts, accepts -1/-2 style input"),
    premium: float = typer.Option(..., "--premium", help="Premium per share"),
    opened_date: str = typer.Option("", "--opened-date", help="Open date YYYY-MM-DD"),
    fees: float = typer.Option(0.0, "--fees", help="Open fees"),
    intent: str = typer.Option("lower_price_entry", "--intent", help="income | lower_price_entry | staged_build | other"),
    notes: str = typer.Option("", "--notes", help="Optional notes"),
    decision_file: str = typer.Option("", "--decision-file", help="Optional linked decision path"),
):
    """Record a new sold put contract."""
    init_db()
    row = create_option_contract(
        underlying_symbol=symbol,
        expiry_date=date.fromisoformat(expiry),
        strike=strike,
        contracts=contracts,
        premium_per_share=premium,
        opened_date=date.fromisoformat(opened_date) if opened_date else None,
        fees=fees,
        intent=intent,
        notes=notes,
        linked_decision_file=decision_file,
    )
    console.print(
        f"[green]OK[/green] Sold put saved: #{row.id} {row.underlying_symbol} {row.expiry_date} {row.strike}P x{row.contracts}  reserved_cash={row.reserved_cash:.2f}  effective_entry={row.effective_entry_if_assigned:.2f}"
    )


@app.command("list")
def list_entries(
    status: str = typer.Option("", "--status", help="open | expired | assigned | closed"),
):
    """List sold put contracts."""
    init_db()
    rows = list_option_contracts(status=status or None)
    if not rows:
        console.print("[yellow]No option contracts found.[/yellow]")
        return
    table = Table(title="Sold Put Contracts")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Underlying", style="cyan")
    table.add_column("Expiry")
    table.add_column("Strike", justify="right")
    table.add_column("Contracts", justify="right")
    table.add_column("Premium", justify="right")
    table.add_column("Reserved", justify="right")
    table.add_column("Status")
    for r in rows:
        table.add_row(
            str(r.id),
            r.underlying_symbol,
            str(r.expiry_date),
            f"{r.strike:.2f}",
            str(r.contracts),
            f"{r.premium_per_share:.2f}",
            f"{r.reserved_cash:.2f}",
            r.status,
        )
    console.print(table)


@app.command("summary")
def summary(
    refresh: bool = typer.Option(False, "--refresh", help="Refresh current spot prices first"),
):
    """Show contingent exposure summary for open sold puts."""
    result = get_option_summary(refresh=refresh)
    console.print_json(json.dumps(result, ensure_ascii=False))


@app.command("assign")
def assign(
    contract_id: int = typer.Argument(...),
    assignment_price: float = typer.Option(None, "--price", help="Assignment price; defaults to strike"),
    assigned_date: str = typer.Option("", "--date", help="Assignment date YYYY-MM-DD"),
    notes: str = typer.Option("", "--notes"),
    apply_to_spot: bool = typer.Option(False, "--apply-to-spot", help="Also update spot position and cash using effective net entry"),
):
    """Mark a sold put as assigned."""
    init_db()
    row = mark_option_assigned(
        contract_id,
        assigned_date=date.fromisoformat(assigned_date) if assigned_date else None,
        assignment_price=assignment_price,
        notes=notes,
        apply_to_spot=apply_to_spot,
    )
    console.print(f"[green]OK[/green] Option #{row.id} marked assigned for {row.underlying_symbol}.")


@app.command("expire")
def expire(
    contract_id: int = typer.Argument(...),
    expired_date: str = typer.Option("", "--date", help="Expiry date YYYY-MM-DD"),
    notes: str = typer.Option("", "--notes"),
):
    """Mark a sold put as expired worthless."""
    init_db()
    row = mark_option_expired(
        contract_id,
        expired_date=date.fromisoformat(expired_date) if expired_date else None,
        notes=notes,
    )
    console.print(f"[green]OK[/green] Option #{row.id} marked expired for {row.underlying_symbol}.")


@app.command("close")
def close(
    contract_id: int = typer.Argument(...),
    cost_to_close: float = typer.Option(..., "--cost-to-close", help="Cost to close the short option"),
    closed_date: str = typer.Option("", "--date", help="Close date YYYY-MM-DD"),
    notes: str = typer.Option("", "--notes"),
):
    """Mark a sold put as closed."""
    init_db()
    row = mark_option_closed(
        contract_id,
        closed_date=date.fromisoformat(closed_date) if closed_date else None,
        realized_cost_to_close=cost_to_close,
        notes=notes,
    )
    console.print(f"[green]OK[/green] Option #{row.id} marked closed for {row.underlying_symbol}.")
