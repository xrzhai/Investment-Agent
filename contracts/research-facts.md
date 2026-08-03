# Research Fact Contract

## Files per symbol

```text
coverage/{SYMBOL}/
├─ status.json
├─ summary.md
├─ facts.jsonl
├─ sources.json
├─ current.md
├─ vN_YYYY-MM-DD.md
├─ source_docs/
└─ archive/
```

Legacy symbols may omit the first four files. New work should create them before adding more unstructured notes.

## Source record

Required:

- `source_id`: stable within the symbol;
- `title`;
- `source_type`;
- `publisher`;
- `published_at` or an explicit reason it is unknown;
- `primary`: whether this is a primary source;
- at least one of `url` or `local_path`.

`local_path` is relative to that symbol's coverage directory and cannot escape
it. External locations use a URL or are copied into `source_docs/` first.

Recommended:

- `retrieved_at`;
- `sha256` for local artifacts;
- `notes` describing scope or limitations.

Use `published_at_unknown_reason` for the explicit unknown-date reason.

## Fact record

Each JSONL line is one atomic claim. Required:

- `fact_id`;
- `symbol`;
- `fact_key`: stable semantic key, such as `revenue.fy2025`;
- `statement`;
- `fact_type`: `reported`, `guidance`, `consensus`, `assumption`, or `inference`;
- `source_ids`;
- `status`: `active`, `superseded`, `disputed`, or `unverified`;
- `recorded_at`.

Use `period`, `as_of`, `available_at`, `value`, `unit` and `locator` when
applicable. `as_of` describes the measured state; `available_at` describes when
the information could first have entered a decision. Historical context filters
use `available_at`, falling back conservatively to `recorded_at`.

## Update semantics

- Reported historical facts are immutable except for documented restatements.
- A newer estimate supersedes an older estimate through `supersedes`.
- `facts.jsonl` remains append-only. The loader treats a referenced prior fact
  as logically superseded; it does not rewrite the earlier JSONL line.
- Conflicting sources remain visible and use `disputed` until resolved.
- Thesis text may summarize facts but does not replace them.
- Facts are selected by task topic and as-of date before entering context.
