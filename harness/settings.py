from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HarnessPaths:
    """Resolved repository paths.

    Paths are injected instead of stored as import-time globals so tests and
    alternate private workspaces can use isolated roots.

    Layout: ``research/`` (coverage, topics, macro, context) and
    ``portfolio/`` (principles, profile, records, data).
    """

    root: Path
    research: Path
    coverage: Path
    portfolio: Path
    data: Path

    @classmethod
    def discover(cls, root: str | Path | None = None) -> "HarnessPaths":
        resolved = (
            Path(root).expanduser().resolve()
            if root is not None
            else Path(__file__).resolve().parents[1]
        )
        research = resolved / "research"
        portfolio = resolved / "portfolio"
        return cls(
            root=resolved,
            research=research,
            coverage=research / "coverage",
            portfolio=portfolio,
            data=portfolio / "data",
        )

    @property
    def portfolio_db(self) -> Path:
        return self.data / "investment.db"

    @property
    def profile_file(self) -> Path:
        return self.portfolio / "profile.json"

    @property
    def principles_file(self) -> Path:
        return self.portfolio / "principles.md"

    @property
    def research_context_file(self) -> Path:
        return self.research / "context.md"
