# Portfolio Review

## Goal

Review exposure, cash, concentration, option obligations and research attention without rereading every full thesis.

## Context

Load:

- current portfolio state from `harness.portfolio`;
- investor profile and policy rules;
- open option exposure;
- one bounded research summary/status per held symbol;
- recent portfolio events since the last review.

Do not load full theses or source documents in the first pass.

## Steps

1. Validate quote freshness and missing FX/price inputs.
2. Compute weights, cash, contingent option exposure and policy signals.
3. Join each holding with research status: thesis version, last review, IC state, next trigger and evidence gaps.
4. Rank attention items by evidence/risk urgency, not by daily P&L.
5. If a symbol needs deeper work, create a separate `thesis-review` task.

## Output

Archive a concise review containing snapshot as-of time, data-quality warnings, exposure summary, research freshness and next actions. A review does not imply a trade.
