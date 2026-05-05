import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cli import analyze


def test_suggest_converts_position_rows_with_portfolio_engine():
    row = SimpleNamespace(symbol="NVDA", quantity=1.0, avg_cost=100.0, current_price=120.0)
    position = SimpleNamespace(symbol="NVDA")
    profile = SimpleNamespace(style="quality_growth")

    with (
        patch.object(analyze, "init_db"),
        patch("app.repositories.portfolio_repo.list_positions", return_value=[row]),
        patch("app.engines.portfolio_engine.compute_positions", return_value=[position]) as compute_positions,
        patch("app.services.profile_service.load_profile", return_value=profile),
        patch("app.engines.recommendation_engine.generate_suggestions", return_value=[]) as generate_suggestions,
    ):
        analyze.suggest()

    compute_positions.assert_called_once_with([row])
    generate_suggestions.assert_called_once_with([position], profile)
