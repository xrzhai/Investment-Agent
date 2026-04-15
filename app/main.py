"""
Investment Agent CLI entry point.
Usage: python app/main.py --help
"""
import typer

from app.cli import portfolio, profile, analyze, journal

app = typer.Typer(
    name="investment-agent",
    help="Personal investment copilot — track holdings, apply philosophy, get explainable suggestions.",
    add_completion=False,
)

app.add_typer(portfolio.app, name="portfolio")
app.add_typer(profile.app, name="profile")
app.add_typer(analyze.app, name="analyze")
app.add_typer(journal.app, name="journal")


if __name__ == "__main__":
    app()
