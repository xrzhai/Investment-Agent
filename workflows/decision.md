# Position Decision

## Goal

Decide whether to initiate, add, hold, trim or exit a single position.

## Context

This is the normal workflow that combines both domains:

- one symbol's current thesis, relevant facts and source metadata;
- current portfolio state, cash, exposure and policy constraints;
- previous approved decision for the same unresolved action, if any.

Archives and unrelated symbols' full theses remain excluded.

## Required structure

1. **Research evidence** — thesis version, facts, falsifiers and uncertainty.
2. **Portfolio constraints** — current/contingent weight, cash, concentration and alternatives.
3. **Decision** — action, size boundary, price/condition boundary and expiry.
4. **Disconfirming evidence** — what would cancel the action.
5. **Execution gate** — explicit statement that this is not an execution record.

Save the decision under `reviews/decisions/` using the decision template.
Keep status `draft` while reasoning is under review. Change only the status to
`approved` after explicit user approval; a generated decision is not
self-approving.
