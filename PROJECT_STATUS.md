# Investment Agent — Current Status

> Last updated: 2026-04-15
> This file describes the current repo shape after the agent-neutral refactor.
> Older slash-command and Claude-specific implementation details are now historical and no longer define the active architecture.

---

## Current positioning

Investment-Agent is now positioned as:
- a thesis-driven portfolio workflow project
- a tool-first automation surface for AI agents
- a thin-CLI project for manual atomic operations
- not a frontend product
- not a generic agent framework

---

## Current architecture

### 1. Core logic
- `app/engines/`
- `app/services/`
- `app/repositories/`
- `app/models/`

This layer owns:
- deterministic calculations
- data access
- market data integration
- thesis loading
- LLM wrapper logic

### 2. Tool layer
- `app/tools/portfolio_tools.py`
- `app/tools/policy_tools.py`
- `app/tools/position_meta_tools.py`
- `app/tools/pnl_tools.py`
- `app/tools/cn_market_data_tools.py`
- `app/tools/postmortem_tools.py`

This is the primary automation surface for agents.

### 3. Thin CLI
- `python run.py portfolio ...`
- `python run.py analyze ...`
- `python run.py profile ...`
- `python run.py journal ...`

CLI is intentionally narrow and is meant for:
- manual import / refresh / summary / check
- local smoke tests
- simple one-shot usage without an agent

### 4. Workflow docs
- `skills/investment-agent/README.md`
- `skills/investment-agent/project-context.md`
- `skills/investment-agent/workflows/*.md`

This is now the main workflow layer for agent-assisted operation.

---

## Current repo structure

```text
investment-agent/
├── run.py
├── app/
│   ├── cli/
│   ├── engines/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── prompts/
│   └── tools/
├── skills/
│   └── investment-agent/
│       ├── README.md
│       ├── project-context.md
│       └── workflows/
├── coverage/
├── reviews/
├── config/
├── data/
└── PROJECT_STATUS.md
```

---

## What changed in the refactor

### Completed
- introduced agent-neutral workflow docs under `skills/investment-agent/`
- repositioned README around tools + workflows + thin CLI
- removed the `.claude/` adapter layer
- removed the `daily` CLI orchestration command
- neutralized active prompt/tool wording that depended on Claude Code
- made the LLM command configurable through `INVESTMENT_AGENT_LLM_CMD`
- migrated postmortem workflows into `skills/investment-agent/workflows/`
- migrated PM suggest and researcher analyze/note/status workflows into `skills/investment-agent/workflows/`

### Intentionally preserved
- deterministic Python portfolio logic
- coverage thesis files and version pointers
- reviews archive
- postmortem tool and DB-backed mistake memory
- default `claude` backend command for LLM generation

---

## Current workflow coverage in `skills/`

Implemented:
- daily review
- PM suggest
- researcher initiate
- researcher update
- researcher analyze
- researcher note
- researcher status
- risk IC sweep
- trader decide
- trader record
- postmortem create
- postmortem list
- postmortem self-check

Still good candidates for later migration / cleanup:
- PM snapshot / curve / cashflow
- additional cleanup of historical references inside old archived outputs

---

## Validation status

Recent refactor validation has included:
- git-based PR-by-PR refactor progression
- compile check of active Python modules via `python3 -m compileall`
- manual repo-structure review
- independent diff review before PR creation

Environment note:
- runtime CLI smoke tests may depend on local Python environment packages such as `typer`
- A-share workflows still depend on `.env` credentials for JQData

---

## Legacy notes

Historical files under `reviews/` and older archived outputs may still reference:
- slash commands
- Claude-specific task names
- older workflow wording

Those references are archival, not authoritative.
The current authoritative workflow surface is:
- `README.md`
- `skills/investment-agent/`
- active Python code under `app/`
