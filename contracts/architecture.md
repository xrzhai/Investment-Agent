# Harness Architecture

## Boundary

The repository provides state, deterministic tools, workflow contracts and audit trails. Reasoning and orchestration belong to the external Agent.

```text
External Agent
    |
    | reads task contract and calls deterministic functions
    v
Research Harness ---------------- Portfolio Harness
files + evidence                  SQLite + calculations
    |                                  |
    +------------ Decision ------------+
```

Research and Portfolio are separate domains. `decision` is the only normal workflow that loads both a full single-company thesis and portfolio constraints.

## Stable components

- context routing;
- research status, fact and source schemas;
- current-thesis pointer convention;
- portfolio event and quote recording;
- deterministic calculations and policy checks;
- validation and audit outputs.

## Explicit non-goals

- embedded LLM clients;
- product CLI or UI;
- autonomous trading;
- generic Agent framework;
- automatic ingestion of every file into context;
- treating market-data provider output as verified research evidence.

## Storage

Long-form and source-linked research remains file-based because it is readable and reviewable. Transactional portfolio facts remain in SQLite because atomicity, uniqueness and queries matter more than direct textual readability.

SQLite is not an Agent. It is a Harness storage adapter.
