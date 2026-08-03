# Migration Notes

## What changed

The repository changed from a CLI application with an embedded LLM into a
deterministic harness operated by an external Agent.

Removed application concepts:

- product CLI commands and shell wrappers;
- embedded model clients and prompts;
- automated recommendation generation;
- duplicate repository/tool layers;
- runtime market-data provider selection.

Retained business domains:

- versioned fundamental research and source lineage;
- current positions, cash, options, quotes and snapshots;
- portfolio policy checks;
- decision, execution and postmortem records.

## Existing SQLite database

`data/investment.db` remains the private portfolio database. The new adapter is
compatible with the existing position, option, snapshot and cashflow tables and
adds two tables on first explicit use:

- `portfolio_events` for the append-only audit log;
- `quotes` for sourced price observations.

Legacy recommendation, journal and mistake-memory tables are not loaded into
normal context. They are left untouched in an existing database so historical
records are not destroyed.

Before migrating the live database:

1. copy `data/investment.db` to a dated backup outside the repository or beside
   it under `data/`;
2. run the test suite against an isolated database;
3. call `PortfolioStore.bootstrap_legacy_events()` once to create idempotent
   baseline events and copy existing instrument classifications into their
   persistent table;
4. validate row counts and current position totals;
5. only then use the new mutation methods for future records.

The migration is deliberately explicit. Importing `harness` does not modify the
database.

## Existing research directories

Legacy `coverage/{SYMBOL}` directories continue to work through `current.md`.
For a symbol being actively reviewed, call
`ResearchStore.ensure_scaffold(symbol)` to add `status.json`, `summary.md`,
`facts.jsonl` and `sources.json` without rewriting thesis history. Migrate
symbols incrementally instead of generating a large, low-quality fact dump.
The generated summary is intentionally a placeholder; the harness never copies
an entire legacy thesis into a supposedly bounded summary.
For an existing thesis, the scaffold keeps `legacy_layout: true`. Change it to
`false` only after a human/Agent review has produced a clean bounded summary and
checked the current thesis for domain separation.
