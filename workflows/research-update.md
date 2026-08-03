# Research Update

## Goal

Create or update official company coverage from source-linked evidence.

## Context

Load symbol status, summary, active facts and the current thesis. Load only source excerpts needed to validate changed claims. Exclude portfolio state.

## Steps

1. State the update trigger and as-of date.
2. Identify facts added, superseded, disputed or still missing.
3. Update only thesis sections affected by new evidence.
4. Re-evaluate business drivers, financial trajectory, valuation assumptions and falsifiers.
5. Create a new `vN_YYYY-MM-DD.md`; never overwrite the current version.
6. Update `current.md`, `status.json` and bounded `summary.md` only after the new version is complete.
7. Preserve an evidence map from material thesis claims to fact/source IDs.

## Guardrails

- Do not insert current position weight, cost basis or P&L into the thesis.
- Do not turn a provider field into a verified fact without checking period and definition.
- If no substantive conclusion changed, a fact refresh or event note is preferable to a new thesis version.
