"""Journal and recommendation persistence."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlmodel import select

from app.models.db import JournalEntryRow, RecommendationRow, get_session
from app.models.domain import JournalEntry, Recommendation


def save_recommendation(rec: Recommendation) -> RecommendationRow:
    with get_session() as session:
        row = RecommendationRow(
            timestamp=rec.timestamp,
            scope=rec.scope,
            action=rec.action.value,
            reason=rec.reason,
            evidence=json.dumps(rec.evidence),
            risk_notes=json.dumps(rec.risk_notes),
            confidence=rec.confidence,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_recommendations(scope: Optional[str] = None, limit: int = 20) -> list[RecommendationRow]:
    with get_session() as session:
        q = select(RecommendationRow).order_by(RecommendationRow.timestamp.desc()).limit(limit)
        if scope:
            q = q.where(RecommendationRow.scope == scope)
        return session.exec(q).all()


def save_journal_entry(entry: JournalEntry) -> JournalEntryRow:
    with get_session() as session:
        row = JournalEntryRow(
            timestamp=entry.timestamp,
            scope=entry.scope,
            thesis=entry.thesis,
            user_note=entry.user_note,
            agent_note=entry.agent_note,
            linked_rec_ids=json.dumps(entry.linked_rec_ids),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_journal_entries(scope: Optional[str] = None, limit: int = 20) -> list[JournalEntryRow]:
    with get_session() as session:
        q = select(JournalEntryRow).order_by(JournalEntryRow.timestamp.desc()).limit(limit)
        if scope:
            q = q.where(JournalEntryRow.scope == scope)
        return session.exec(q).all()
