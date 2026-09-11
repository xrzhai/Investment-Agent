from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HarnessPaths:
    """Resolved repository paths.

    Paths are injected instead of stored as import-time globals so tests and
    alternate private workspaces can use isolated roots.
    """

    root: Path
    coverage: Path
    reviews: Path
    data: Path
    config: Path
    research_notes: Path

    @classmethod
    def discover(cls, root: str | Path | None = None) -> "HarnessPaths":
        resolved = (
            Path(root).expanduser().resolve()
            if root is not None
            else Path(__file__).resolve().parents[1]
        )
        return cls(
            root=resolved,
            coverage=resolved / "coverage",
            reviews=resolved / "reviews",
            data=resolved / "data",
            config=resolved / "config",
            research_notes=resolved / "research_notes",
        )

    @property
    def portfolio_db(self) -> Path:
        return self.data / "investment.db"

    @property
    def profile_file(self) -> Path:
        return self.config / "profile.json"

    @property
    def principles_file(self) -> Path:
        return self.config / "principles.md"
