"""CLI commands: journal *"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from app.models.db import init_db
from app.models.domain import JournalEntry
from app.repositories.journal_repo import list_journal_entries, save_journal_entry

app = typer.Typer(help="Record and review your investment journal.")
console = Console()


@app.command("add")
def add(
    scope: str = typer.Argument(..., help="Ticker or 'portfolio'"),
    thesis: str = typer.Option("", "--thesis", "-t", help="Investment thesis"),
    note: str = typer.Option("", "--note", "-n", help="Personal note"),
):
    """Add a journal entry for a position or the overall portfolio."""
    init_db()
    scope = scope.upper() if scope.lower() != "portfolio" else "portfolio"
    entry = JournalEntry(scope=scope, thesis=thesis, user_note=note)
    row = save_journal_entry(entry)
    console.print(f"[green]OK[/green] Journal entry #{row.id} saved for {scope}.")


@app.command("list")
def list_entries(
    scope: str = typer.Argument("", help="Filter by ticker or 'portfolio' (leave blank for all)"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
    """List recent journal entries."""
    init_db()
    rows = list_journal_entries(scope.upper() if scope else None, limit=limit)
    if not rows:
        console.print("[yellow]No entries found.[/yellow]")
        return

    table = Table(title="Journal Entries")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Scope")
    table.add_column("Thesis")
    table.add_column("Note")

    for r in rows:
        table.add_row(
            str(r.id),
            r.timestamp.strftime("%Y-%m-%d"),
            r.scope,
            (r.thesis[:60] + "…") if len(r.thesis) > 60 else r.thesis,
            (r.user_note[:60] + "…") if len(r.user_note) > 60 else r.user_note,
        )
    console.print(table)


@app.command("review")
def review(scope: str = typer.Argument(..., help="Ticker or 'portfolio'")):
    """Show all journal entries for a specific scope."""
    init_db()
    scope = scope.upper() if scope.lower() != "portfolio" else "portfolio"
    rows = list_journal_entries(scope, limit=50)
    if not rows:
        console.print(f"[yellow]No entries for {scope}.[/yellow]")
        return

    for r in rows:
        console.rule(f"#{r.id}  {r.timestamp.strftime('%Y-%m-%d %H:%M')}")
        if r.thesis:
            console.print(f"[bold]Thesis:[/bold] {r.thesis}")
        if r.user_note:
            console.print(f"[bold]Note:[/bold] {r.user_note}")
        if r.agent_note:
            console.print(f"[bold]Agent:[/bold] {r.agent_note}")
        console.print()


@app.command("research")
def research(
    symbol: str = typer.Argument(..., help="Ticker symbol"),
    type_: str = typer.Option(..., "--type", "-t", help="Research type: earnings | dcf | comps | note"),
    content: str = typer.Option(..., "--content", "-c", help="Key conclusions to persist"),
):
    """Persist key conclusions from a skill run (earnings, DCF, comps) as a journal note."""
    init_db()
    symbol = symbol.upper()
    entry = JournalEntry(
        scope=symbol,
        user_note=f"[{type_}]",
        agent_note=content,
    )
    row = save_journal_entry(entry)
    console.print(f"[green]OK[/green] Research note #{row.id} saved for {symbol} ({type_}).")
