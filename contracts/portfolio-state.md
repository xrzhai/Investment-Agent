# Portfolio State Contract

## Scope

Portfolio management is necessary but low-frequency. The system optimizes for correctness and auditability rather than high-throughput trading.

## Structured facts

SQLite stores:

- current position read models;
- append-only portfolio events;
- cashflow events;
- option contracts and state transitions;
- sourced quote observations;
- portfolio snapshots.
- persistent instrument classifications (sector, region, style, themes and
  risk label) used for exposure summaries.

Research documents do not store live quantity, cost or P&L as canonical facts.
Instrument classifications are stored independently of current position rows so
closing a position does not erase reusable exposure metadata.

## Event discipline

Every future mutation should produce an event with:

- stable `event_id`;
- `event_type`;
- `occurred_at`;
- affected symbol when applicable;
- structured payload;
- `source` and optional `source_ref`;
- `recorded_at`.

For trades and option executions, the event ID is derived from a stable external
`execution_ref`. Retrying the same execution is rejected before any cash or
position mutation. The separate `decision_ref` preserves the reason/execution
boundary.

External deposits and withdrawals similarly require a stable `cashflow_ref` so
an Agent retry cannot duplicate cash.

Position rows are current read models. Events provide the audit trail.

Normal equity trades update the affected position, settlement-currency cash and
event log in one transaction. Short-put opening/closing/assignment likewise
updates its contract state and related cash/position read models atomically.
External deposits and withdrawals use cashflow records; they must not duplicate
trade settlement cash.

## Quote discipline

A price is not just a number. Record:

- symbol;
- price and currency;
- market as-of time;
- provider/source;
- optional source reference;
- retrieval time.

FX uses the canonical quote symbol `FX:{LOCAL}/{BASE}` and stores the amount of
base currency per one unit of local currency, with the same as-of/source rules.
Quote times are timezone-aware. Historical state selects only observations at
or before its cutoff; state marks price or FX observations older than the
configured freshness window instead of silently presenting them as current.

Research valuation numbers still require research-grade source records; a portfolio quote does not automatically qualify as thesis evidence.

## Domain gate

- Research tasks cannot use cost or P&L as evidence.
- Portfolio reviews may use weight, cash, exposure and policy signals.
- Decisions combine research evidence and portfolio constraints in separate sections.
- Trade recording requires an approved decision reference except for explicit corrections or opening baselines.
