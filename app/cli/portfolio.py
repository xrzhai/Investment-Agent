"""CLI commands: portfolio *"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from app.models.db import init_db
from app.models.domain import Position, PortfolioSnapshot
from app.repositories import portfolio_repo
from app.services.jqdata_provider import is_cn_a_symbol

app = typer.Typer(help="Manage and view your portfolio.")
console = Console()


def _validate_symbol_market(symbol: str, market: str) -> None:
    """Raise if symbol/market combination is invalid."""
    if market == "CN_A" and not is_cn_a_symbol(symbol):
        console.print(
            f"[red]Error:[/red] market=CN_A requires a symbol with .SH/.SZ/.BJ suffix, got: {symbol}"
        )
        raise typer.Exit(1)
    if market == "US" and is_cn_a_symbol(symbol):
        console.print(
            f"[red]Error:[/red] Symbol {symbol} looks like an A-share. Use --market CN_A."
        )
        raise typer.Exit(1)


@app.command("add")
def add_position(
    symbol: str = typer.Argument(..., help="Ticker symbol, e.g. AAPL or 600519.SH"),
    quantity: float = typer.Argument(..., help="Number of shares"),
    cost: float = typer.Option(..., "--cost", "-c", help="Average cost per share (in local currency)"),
    market: str = typer.Option("US", "--market", "-m", help="Market: US or CN_A"),
):
    """Add or update a position."""
    init_db()
    market = market.upper()
    # Auto-detect market from symbol suffix if not overridden
    if market == "US" and is_cn_a_symbol(symbol):
        market = "CN_A"
    _validate_symbol_market(symbol, market)
    portfolio_repo.upsert_position(symbol.upper(), quantity, cost, market=market)
    currency = "CNY" if market == "CN_A" else "USD"
    console.print(
        f"[green]OK[/green] Position saved: {symbol.upper()}  market={market}  "
        f"currency={currency}  qty={quantity}  avg_cost={cost}"
    )


@app.command("remove")
def remove_position(symbol: str = typer.Argument(..., help="Ticker symbol to remove")):
    """Remove a position."""
    init_db()
    symbol = symbol.upper()
    if portfolio_repo.delete_position(symbol):
        console.print(f"[yellow]Removed {symbol}[/yellow]")
    else:
        console.print(f"[red]{symbol} not found[/red]")


@app.command("import")
def import_csv(
    file: Path = typer.Argument(
        ..., help="CSV file: symbol,quantity,avg_cost[,market]"
    ),
):
    """
    Import positions from CSV.

    Supported formats:
      Old: symbol,quantity,avg_cost          (market defaults to US)
      New: symbol,market,quantity,avg_cost
    """
    init_db()
    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    count = 0
    errors = []
    with open(file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # line 1 = header
            sym = row.get("symbol", "").strip().upper()
            if not sym:
                errors.append(f"Line {i}: missing symbol")
                continue
            try:
                qty = float(row["quantity"])
                cost = float(row["avg_cost"])
            except (KeyError, ValueError) as e:
                errors.append(f"Line {i} ({sym}): {e}")
                continue

            # Market: new format has explicit column; old format defaults to US
            raw_market = row.get("market", "").strip().upper()
            if not raw_market:
                # Auto-detect from symbol suffix
                market = "CN_A" if is_cn_a_symbol(sym) else "US"
            else:
                market = raw_market

            try:
                _validate_symbol_market(sym, market)
            except SystemExit:
                errors.append(f"Line {i} ({sym}): symbol/market mismatch")
                continue

            portfolio_repo.upsert_position(sym, qty, cost, market=market)
            count += 1

    if count:
        console.print(f"[green]OK[/green] Imported {count} positions from {file.name}")
    if errors:
        console.print(f"[yellow]Warnings ({len(errors)}):[/yellow]")
        for e in errors:
            console.print(f"  {e}")


@app.command("summary")
def summary():
    """Show current portfolio summary (USD-based totals for mixed portfolios)."""
    init_db()
    rows = portfolio_repo.list_positions()
    if not rows:
        console.print("[yellow]No positions found. Use 'portfolio add' or 'portfolio import'.[/yellow]")
        return

    from app.engines.portfolio_engine import compute_positions
    positions = compute_positions(rows)
    total_base = sum(p.base_market_value for p in positions)
    total_cost_usd = sum(
        p.avg_cost * p.quantity * p.fx_rate_to_base for p in positions
    )
    total_pnl = total_base - total_cost_usd

    has_cn = any(p.market == "CN_A" for p in positions)
    title = f"Portfolio Summary  |  Total Value (USD): ${total_base:,.2f}"

    table = Table(title=title)
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Mkt", style="dim")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Local MV", justify="right")
    table.add_column("USD MV", justify="right")
    table.add_column("PnL (local)", justify="right")
    table.add_column("PnL %", justify="right")
    table.add_column("Weight %", justify="right")

    for p in sorted(positions, key=lambda x: -x.base_market_value):
        pnl_color = "green" if p.unrealized_pnl >= 0 else "red"
        ccy = p.currency
        price_str = f"{ccy} {p.current_price:.2f}" if p.current_price else "[dim]N/A[/dim]"
        local_mv_str = f"{ccy} {p.local_market_value:,.0f}" if p.local_market_value else "[dim]N/A[/dim]"
        usd_mv_str = f"${p.base_market_value:,.2f}" if p.base_market_value else "[dim]N/A[/dim]"
        table.add_row(
            p.symbol,
            p.market,
            f"{p.quantity:,.2f}",
            price_str,
            local_mv_str,
            usd_mv_str,
            f"[{pnl_color}]{ccy} {p.unrealized_pnl:+,.0f}[/{pnl_color}]" if p.market_value else "[dim]N/A[/dim]",
            f"[{pnl_color}]{p.unrealized_pnl_pct:+.1f}%[/{pnl_color}]" if p.market_value else "[dim]N/A[/dim]",
            f"{p.weight:.1f}%",
        )

    console.print(table)
    if has_cn:
        # Show FX rate used
        sample_cn = next(p for p in positions if p.market == "CN_A")
        stale_note = " [yellow](stale)[/yellow]" if sample_cn.fx_stale else ""
        console.print(f"FX: 1 CNY = {sample_cn.fx_rate_to_base:.4f} USD{stale_note}")
    if total_base:
        pnl_color = "green" if total_pnl >= 0 else "red"
        console.print(f"Total PnL (USD): [{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}]")
    else:
        console.print("[dim]Prices not loaded. Run 'portfolio refresh' first.[/dim]")


@app.command("snapshot")
def snapshot():
    """Save today's portfolio snapshot to DB."""
    init_db()
    rows = portfolio_repo.list_positions()
    if not rows:
        console.print("[yellow]No positions to snapshot.[/yellow]")
        return

    from app.engines.portfolio_engine import compute_positions
    positions = compute_positions(rows)
    total_value = sum(p.base_market_value for p in positions)
    top_weight = max((p.weight for p in positions), default=0)

    from datetime import timedelta
    yesterday = date.today() - timedelta(days=1)
    prev = portfolio_repo.get_snapshot(yesterday)
    daily_return_pct = 0.0
    if prev and prev.total_value:
        daily_return_pct = (total_value - prev.total_value) / prev.total_value * 100

    snap = PortfolioSnapshot(
        snapshot_date=date.today(),
        total_value=total_value,
        positions=positions,
        daily_return_pct=daily_return_pct,
        top_position_weight=top_weight / 100,
    )
    portfolio_repo.save_snapshot(snap)
    console.print(f"[green]OK[/green] Snapshot saved for {date.today()}  total(USD)=${total_value:,.2f}")


@app.command("check")
def check():
    """Run policy checks against your investor profile."""
    init_db()
    from app.engines.policy_engine import run_policy_check
    from app.engines.portfolio_engine import compute_positions
    from app.services.profile_service import load_profile

    rows = portfolio_repo.list_positions()
    if not rows:
        console.print("[yellow]No positions.[/yellow]")
        return

    positions = compute_positions(rows)
    profile = load_profile()
    result = run_policy_check(positions, profile)

    if not result.has_violations:
        console.print("[green]OK All policy checks passed. Portfolio is within defined bounds.[/green]")
    else:
        console.print(f"[red]!  {len(result.triggers)} policy trigger(s) found:[/red]\n")
        for t in result.triggers:
            scope = f"[{t.symbol}]" if t.symbol else "[portfolio]"
            console.print(f"  {scope}  {t.message}")


@app.command("refresh")
def refresh():
    """Fetch latest prices from market data sources and update positions."""
    init_db()
    from app.services.market_data import get_batch_prices

    rows = portfolio_repo.list_positions()
    if not rows:
        console.print("[yellow]No positions.[/yellow]")
        return

    symbols = [r.symbol for r in rows]
    cn_count = sum(1 for s in symbols if is_cn_a_symbol(s))
    console.print(
        f"Fetching prices for: {', '.join(symbols)} "
        f"({'A股: ' + str(cn_count) + ' via JQData, ' if cn_count else ''}"
        f"US: {len(symbols) - cn_count} via yfinance) ..."
    )
    prices = get_batch_prices(symbols)

    updated = 0
    for sym, price in prices.items():
        if price:
            portfolio_repo.update_price(sym, price)
            updated += 1

    console.print(f"[green]OK[/green] Updated {updated}/{len(symbols)} prices.")
    # Auto-snapshot after refresh
    snapshot()
