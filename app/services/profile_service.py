"""Investor profile persistence (JSON file-based for MVP)."""
from __future__ import annotations

import json
from pathlib import Path

from app.models.domain import InvestorProfile

PROFILE_PATH = Path(__file__).parent.parent.parent / "config" / "profile.json"


def load_profile() -> InvestorProfile:
    if not PROFILE_PATH.exists():
        return InvestorProfile()
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return InvestorProfile.model_validate(json.load(f))


def save_profile(profile: InvestorProfile) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)
