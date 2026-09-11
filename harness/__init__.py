"""Optional deterministic helpers for the Investment Research Harness.

Research agents can read the repository's Markdown directly.  This package is
only for structured research records and portfolio operations that benefit
from deterministic code.

No umbrella API class: import the submodules you need
(``harness.portfolio.*`` for portfolio transactions/valuation,
``harness.settings`` for path discovery) or just read the repository's
Markdown and JSONL files.
"""

from harness.settings import HarnessPaths

__all__ = [
    "HarnessPaths",
]
