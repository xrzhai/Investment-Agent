"""Investment principles loader (Markdown file-based)."""
from __future__ import annotations

from pathlib import Path

PRINCIPLES_PATH = Path(__file__).parent.parent.parent / "config" / "principles.md"


def load_principles() -> str | None:
    """Return full principles markdown text, or None if file missing/empty."""
    if not PRINCIPLES_PATH.exists():
        return None
    text = PRINCIPLES_PATH.read_text(encoding="utf-8").strip()
    return text if text else None
