from __future__ import annotations

import pytest

from harness.context import ContextRequest, ContextRouter, ContextTask
from harness.portfolio.service import PortfolioService
from harness.portfolio.store import PortfolioStore
from harness.research.store import ResearchStore


class ExplodingPortfolio:
    def get_state(self):
        raise AssertionError("research-only task attempted to load portfolio state")


def test_research_scan_never_loads_portfolio_or_full_thesis(harness_paths):
    router = ContextRouter(ResearchStore(harness_paths), ExplodingPortfolio())

    pack = router.build(ContextRequest(task=ContextTask.research_scan, symbol="ABC"))

    assert pack.portfolio_state is None
    assert {document.role for document in pack.documents} == {"research_summary"}
    assert "cost basis" in pack.excluded
    assert "P&L" in pack.excluded
    assert [fact.fact_id for fact in pack.facts] == ["fact-1"]
    assert [source.source_id for source in pack.sources] == ["src-1"]


def test_decision_loads_one_thesis_and_current_portfolio(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    service = PortfolioService(store, paths=harness_paths)
    router = ContextRouter(ResearchStore(harness_paths), service)

    pack = router.build(ContextRequest(task=ContextTask.decision, symbol="ABC"))

    assert pack.portfolio_state is not None
    assert [document.role for document in pack.documents].count("current_thesis") == 1
    assert not pack.research_overview


def test_portfolio_review_uses_bounded_summary_not_thesis(harness_paths):
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=1_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    service = PortfolioService(store, paths=harness_paths)
    router = ContextRouter(ResearchStore(harness_paths), service)

    pack = router.build(ContextRequest(task=ContextTask.portfolio_review))

    assert [item.symbol for item in pack.research_overview] == ["ABC"]
    assert 0 < len(pack.portfolio_events) <= 50
    assert any(path.endswith("summary.md") for path in pack.loaded_paths)
    assert not any(document.role == "current_thesis" for document in pack.documents)
    assert "all held symbols' full theses" in pack.excluded


def test_legacy_symbol_without_summary_does_not_smuggle_thesis_into_scan(harness_paths):
    symbol_dir = harness_paths.coverage / "LEG"
    symbol_dir.mkdir()
    (symbol_dir / "current.md").write_text("v1.md", encoding="utf-8")
    (symbol_dir / "v1.md").write_text("FULL THESIS SECRET", encoding="utf-8")
    router = ContextRouter(ResearchStore(harness_paths), ExplodingPortfolio())

    pack = router.build(ContextRequest(task=ContextTask.research_scan, symbol="LEG"))

    assert not pack.documents
    assert any("no bounded summary" in warning for warning in pack.warnings)
    assert all("FULL THESIS SECRET" not in document.content for document in pack.documents)


def test_decision_context_obeys_hard_character_budget(harness_paths):
    current = (harness_paths.coverage / "ABC" / "current.md").read_text(encoding="utf-8").strip()
    (harness_paths.coverage / "ABC" / current).write_text("X" * 20_000, encoding="utf-8")
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    store.set_position_baseline(symbol="ABC", quantity=10, avg_cost=90)
    router = ContextRouter(
        ResearchStore(harness_paths),
        PortfolioService(store, paths=harness_paths),
    )

    pack = router.build(ContextRequest(task=ContextTask.decision, symbol="ABC", max_chars=5_000))

    assert pack.total_chars <= 5_000
    assert pack.portfolio_state is not None
    assert any("thesis was truncated" in warning for warning in pack.warnings)


def test_full_thesis_tasks_receive_research_only_view(harness_paths):
    current = (harness_paths.coverage / "ABC" / "current.md").read_text(encoding="utf-8").strip()
    (harness_paths.coverage / "ABC" / current).write_text(
        "# ABC\n\n## Fundamental\nResearch evidence.\n\n"
        "## 头寸管理原则\n当前权重 20%\n目标权重 25%\n\n"
        "## Risks\nResearch risk remains.\n",
        encoding="utf-8",
    )
    router = ContextRouter(ResearchStore(harness_paths), ExplodingPortfolio())

    pack = router.build(ContextRequest(task=ContextTask.research_update, symbol="ABC"))
    thesis = next(document.content for document in pack.documents if document.role == "current_thesis")

    assert "Research evidence" in thesis
    assert "Research risk remains" in thesis
    assert "当前权重" not in thesis
    assert "目标权重" not in thesis
    assert any("portfolio-specific lines" in warning for warning in pack.warnings)


def test_trade_record_loads_only_an_approved_decision_and_portfolio(harness_paths):
    decision_dir = harness_paths.reviews / "decisions"
    decision_dir.mkdir()
    decision = decision_dir / "ABC-approved.md"
    decision.write_text(
        "# Decision\n\n**Status:** approved\n\nBuy at or below 100.\n",
        encoding="utf-8",
    )
    store = PortfolioStore(paths=harness_paths)
    store.set_position_baseline(symbol="CASH_USD", quantity=10_000, avg_cost=1)
    router = ContextRouter(
        ResearchStore(harness_paths),
        PortfolioService(store, paths=harness_paths),
    )

    pack = router.build(
        ContextRequest(
            task=ContextTask.trade_record,
            decision_ref="reviews/decisions/ABC-approved.md",
        )
    )

    assert [document.role for document in pack.documents] == ["approved_decision"]
    assert pack.portfolio_state is not None
    assert not pack.facts


def test_trade_record_rejects_draft_decision(harness_paths):
    decision_dir = harness_paths.reviews / "decisions"
    decision_dir.mkdir()
    (decision_dir / "draft.md").write_text("**Status:** draft\n", encoding="utf-8")
    router = ContextRouter(
        ResearchStore(harness_paths),
        PortfolioService(PortfolioStore(paths=harness_paths), paths=harness_paths),
    )

    with pytest.raises(ValueError, match="not marked approved"):
        router.build(
            ContextRequest(
                task=ContextTask.trade_record,
                decision_ref="reviews/decisions/draft.md",
            )
        )
