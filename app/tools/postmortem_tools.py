"""
Postmortem / Mistake Memory tool.

Manages Agent operational error records — not investment decisions,
but mistakes the agent itself made (data misreads, calculation errors,
logic contradictions, missed steps, format issues).

Usage:
    postmortem_tools.py --create                            # read JSON from stdin, write draft
    postmortem_tools.py --approve <id>                      # draft → active
    postmortem_tools.py --retire <id>                       # → retired
    postmortem_tools.py --recall --task <task_scope> [--symbol <symbol>]
    postmortem_tools.py --list [--status draft|active|retired]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

# Allow running directly from project root
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.models.db import MistakeMemoryRow, get_engine, init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: MistakeMemoryRow) -> dict:
    return {
        "id": row.id,
        "mistake_type": row.mistake_type,
        "task_scope": row.task_scope,
        "symbol_scope": row.symbol_scope,
        "mistake": row.mistake,
        "root_cause": row.root_cause,
        "prevention_rule": row.prevention_rule,
        "trigger_check": row.trigger_check,
        "severity": row.severity,
        "confidence": row.confidence,
        "source": row.source,
        "bad_outcome": row.bad_outcome,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create() -> None:
    """Read JSON from stdin and insert as draft."""
    raw = sys.stdin.read().strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    required = ["mistake_type", "mistake", "root_cause", "prevention_rule", "trigger_check"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        print(json.dumps({"error": f"Missing required fields: {missing}"}))
        sys.exit(1)

    row = MistakeMemoryRow(
        mistake_type=data["mistake_type"],
        task_scope=data.get("task_scope"),
        symbol_scope=data.get("symbol_scope"),
        mistake=data["mistake"],
        root_cause=data["root_cause"],
        prevention_rule=data["prevention_rule"],
        trigger_check=data["trigger_check"],
        severity=data.get("severity", "medium"),
        confidence=float(data.get("confidence", 0.7)),
        source=data.get("source", "user_report"),
        bad_outcome=data.get("bad_outcome"),
        status="draft",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    with Session(get_engine()) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        print(json.dumps({"ok": True, "id": row.id, "status": "draft"}))


def cmd_approve(id_: int) -> None:
    with Session(get_engine()) as session:
        row = session.get(MistakeMemoryRow, id_)
        if not row:
            print(json.dumps({"error": f"ID {id_} not found"}))
            sys.exit(1)
        row.status = "active"
        row.confidence = min(1.0, row.confidence + 0.1)  # slight confidence bump on human approval
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        print(json.dumps({"ok": True, "id": id_, "status": "active"}))


def cmd_retire(id_: int) -> None:
    with Session(get_engine()) as session:
        row = session.get(MistakeMemoryRow, id_)
        if not row:
            print(json.dumps({"error": f"ID {id_} not found"}))
            sys.exit(1)
        row.status = "retired"
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        print(json.dumps({"ok": True, "id": id_, "status": "retired"}))


def cmd_recall(task_scope: Optional[str], symbol: Optional[str], top_k: int = 5) -> None:
    """Return relevant active mistake memories for a given task context."""
    with Session(get_engine()) as session:
        stmt = select(MistakeMemoryRow).where(MistakeMemoryRow.status == "active")
        rows = session.exec(stmt).all()

    # Filter by task_scope
    if task_scope:
        rows = [r for r in rows if r.task_scope in (task_scope, "any", None)]

    # Filter by symbol_scope (include records with no symbol restriction)
    if symbol:
        rows = [r for r in rows if r.symbol_scope in (symbol, None)]
    else:
        rows = [r for r in rows if r.symbol_scope is None]

    # Sort: severity ASC (high first), then confidence DESC
    rows.sort(key=lambda r: (SEVERITY_ORDER.get(r.severity, 1), -r.confidence))

    # Top-K
    rows = rows[:top_k]

    print(json.dumps([_row_to_dict(r) for r in rows], ensure_ascii=False, indent=2))


def cmd_list(status_filter: Optional[str]) -> None:
    with Session(get_engine()) as session:
        stmt = select(MistakeMemoryRow)
        if status_filter:
            stmt = stmt.where(MistakeMemoryRow.status == status_filter)
        rows = session.exec(stmt).all()

    rows_sorted = sorted(rows, key=lambda r: (r.status, SEVERITY_ORDER.get(r.severity, 1)))
    print(json.dumps([_row_to_dict(r) for r in rows_sorted], ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()

    parser = argparse.ArgumentParser(description="Postmortem / Mistake Memory tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true", help="Read JSON from stdin and create draft")
    group.add_argument("--approve", type=int, metavar="ID", help="Approve a draft (→ active)")
    group.add_argument("--retire", type=int, metavar="ID", help="Retire an entry")
    group.add_argument("--recall", action="store_true", help="Recall relevant active entries")
    group.add_argument("--list", action="store_true", help="List all entries")

    parser.add_argument("--task", type=str, help="Task scope for recall (e.g. researcher_update)")
    parser.add_argument("--symbol", type=str, help="Symbol scope for recall")
    parser.add_argument("--status", type=str, choices=["draft", "active", "retired"],
                        help="Filter status for --list")
    parser.add_argument("--top-k", type=int, default=5, help="Max results for --recall")

    args = parser.parse_args()

    if args.create:
        cmd_create()
    elif args.approve is not None:
        cmd_approve(args.approve)
    elif args.retire is not None:
        cmd_retire(args.retire)
    elif args.recall:
        cmd_recall(args.task, args.symbol, args.top_k)
    elif args.list:
        cmd_list(args.status)


if __name__ == "__main__":
    main()
