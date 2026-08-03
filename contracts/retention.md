# Retention and Growth Contract

## Principle

Persist audit facts; do not persist bulk context. Database size and Agent
context size are separate concerns because the Agent receives bounded query
results, never a database dump.

## What is retained

- `portfolio_events`: append-only, compact structured payloads;
- `quotes`: only observations used by a review, decision or execution record;
- `snapshots`: review-time or event-time state, not an automatic daily job;
- `cashflow_events` and option transitions: permanently;
- current position rows: mutable read models backed by events.

Do not store source PDFs, filings, transcripts, thesis prose, model prompts or
Agent conversations as SQLite blobs.

## Expected growth

For a low-frequency portfolio, a conservative year might contain:

- 100 portfolio events at roughly 1–2 KB each;
- 500 sourced quotes at well below 1 KB each;
- 50 compact snapshots with 10–30 positions at roughly 2–10 KB each.

That is normally only a few megabytes per year including indexes. Even a much
busier history is well within SQLite's practical range. The large files in this
repository are source documents and images, not structured portfolio rows.

## Context boundary

- Research tasks query zero portfolio rows.
- Portfolio review reads the current position/option state and bounded research
  summaries; it does not read the full event log.
- Trade recording reads the referenced decision and affected rows only.
- Postmortem requests must specify an event or bounded time window.
- Event queries are capped; bulk export is a maintenance task, not Agent
  context.

## Maintenance

- Back up the SQLite file before a schema migration.
- Run `PRAGMA integrity_check` during a periodic maintenance review.
- Keep events and cashflows; do not delete audit history to save negligible
  space.
- If quotes ever become high frequency, move old quote observations to a dated
  archive database while retaining event references. Do not introduce this
  complexity until measured growth justifies it.
