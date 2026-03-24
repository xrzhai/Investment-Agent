"""Coverage thesis reader — resolves current.md pointer and loads thesis text."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Project root is two levels above this file (app/services/ -> app/ -> project root)
_COVERAGE_ROOT = Path(__file__).parents[2] / "coverage"


def load_thesis(symbol: str) -> Optional[str]:
    """Return full thesis text for *symbol*, or None if no coverage exists."""
    pointer_path = _COVERAGE_ROOT / symbol.upper() / "current.md"
    if not pointer_path.exists():
        return None
    version_filename = pointer_path.read_text(encoding="utf-8").strip()
    if not version_filename:
        return None
    thesis_path = _COVERAGE_ROOT / symbol.upper() / version_filename
    if not thesis_path.exists():
        return None
    return thesis_path.read_text(encoding="utf-8")


def get_coverage_status(symbol: str) -> str:
    """Return 'Active (vN_YYYY-MM-DD)' or 'Not initiated'."""
    pointer_path = _COVERAGE_ROOT / symbol.upper() / "current.md"
    if not pointer_path.exists():
        return "Not initiated"
    version_filename = pointer_path.read_text(encoding="utf-8").strip()
    if not version_filename:
        return "Not initiated"
    # Strip .md suffix for display: "v1_2026-03-17.md" -> "v1_2026-03-17"
    label = version_filename.removesuffix(".md")
    return f"Active ({label})"
