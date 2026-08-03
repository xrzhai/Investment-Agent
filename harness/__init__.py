"""Deterministic core for the Investment Research Harness.

The package intentionally contains no LLM client and no product CLI. External
agents import these functions or use a thin environment-specific adapter.
"""

from harness.context import ContextRequest, ContextRouter, ContextTask
from harness.api import InvestmentHarness
from harness.settings import HarnessPaths

__all__ = [
    "ContextRequest",
    "ContextRouter",
    "ContextTask",
    "HarnessPaths",
    "InvestmentHarness",
]
