from __future__ import annotations

from pathlib import Path
from typing import Mapping

from harness.context import ContextPack, ContextRequest, ContextRouter
from harness.portfolio.models import PolicyReport, PortfolioState
from harness.portfolio.policy import evaluate_policy
from harness.portfolio.service import PortfolioService
from harness.portfolio.store import PortfolioStore
from harness.research.store import ResearchStore
from harness.settings import HarnessPaths
from harness.validation import validate_workspace


class InvestmentHarness:
    """Small Python surface for an external Agent; intentionally no CLI or LLM."""

    def __init__(self, root: str | Path | None = None):
        self.paths = HarnessPaths.discover(root)
        self.research = ResearchStore(self.paths)
        self.portfolio_store = PortfolioStore(paths=self.paths)
        self.portfolio = PortfolioService(self.portfolio_store, paths=self.paths)
        self.context_router = ContextRouter(self.research, self.portfolio)

    def context(self, request: ContextRequest) -> ContextPack:
        return self.context_router.build(request)

    def portfolio_state(
        self,
        *,
        fx_rates_to_base: Mapping[str, float] | None = None,
    ) -> PortfolioState:
        return self.portfolio.get_state(fx_rates_to_base=fx_rates_to_base)

    def portfolio_policy(
        self,
        *,
        fx_rates_to_base: Mapping[str, float] | None = None,
    ) -> PolicyReport:
        state = self.portfolio_state(fx_rates_to_base=fx_rates_to_base)
        return evaluate_policy(state, self.portfolio.load_profile())

    def validate(self):
        return validate_workspace(self.paths.root)
