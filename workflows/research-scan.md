# Research Scan

## Goal

Answer a bounded company or industry question without silently changing official coverage.

## Context

Load:

1. symbol `status.json` or legacy README/current pointer;
2. bounded `summary.md` when present;
3. active facts relevant to the question;
4. source metadata for facts used;
5. targeted source excerpts only if verification is required.

Do not load portfolio state, archives or the full thesis by default.

## Output

Separate:

- verified facts;
- management claims/guidance;
- assumptions or inference;
- unresolved questions;
- whether the result is material enough to trigger `research-update`.

Do not update `current.md` in this workflow.
