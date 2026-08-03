# Investment Research Harness — Agent Contract

## 1. Mission

本仓库是一层投研 Harness。你的职责是依据用户任务，读取最小必要上下文，使用来源化事实完成研究或组合管理，并留下可审计记录。

你不是仓库内置的 Agent，也不能自动交易。

## 2. First route the task

开始前先把任务归入一个且仅一个主类型：

| Task | Default context | Portfolio data | Full thesis | Source documents |
|---|---|---:|---:|---:|
| `research_scan` | status + summary + relevant facts | No | No | No |
| `event_intake` | status + summary + relevant facts | No | No; reroute if material | Targeted only |
| `research_update` | status + current thesis + facts | No | Yes | Targeted only |
| `thesis_review` | status + current thesis + facts | No | Yes | Targeted only |
| `portfolio_review` | portfolio state + per-symbol summaries | Yes | No by default | No |
| `decision` | one symbol research context + portfolio constraints | Yes | Yes, one symbol | Targeted only |
| `trade_record` | approved decision + portfolio state | Yes | No | No |
| `postmortem` | affected artifact + applicable contract | Only if relevant | Only if relevant | Only if relevant |

If the task is ambiguous, default to `research_scan`, the least contaminating context.

## 3. Mandatory read order

1. Read this file.
2. Read `contracts/context-policy.md`.
3. Read the one matching file in `workflows/`.
4. For a symbol task, read in this order:
   - `coverage/{SYMBOL}/status.json` if present;
   - otherwise `coverage/{SYMBOL}/README.md` and `current.md`;
   - `summary.md` if present;
   - `facts.jsonl`, filtered to the task topics and as-of date;
   - current thesis only when the routing table allows it;
   - `sources.json` metadata for facts actually used;
   - source document excerpts only when a claim must be verified.

Never begin by recursively listing or reading all of `coverage/`.

## 4. Excluded by default

Do not load these unless the selected workflow explicitly requires them:

- `coverage/*/archive/`;
- old thesis versions not pointed to by `current.md`;
- `coverage/*/source_docs/` full contents;
- `research_notes/`;
- historical `reviews/`;
- raw database dumps;
- cost basis, unrealized P&L or trading history during pure research;
- another symbol's thesis during a single-company task.

File presence is not permission to include it in context.

## 5. Research fact rules

- Every material factual claim needs `source_id`, `as_of` or `period`, and an evidence locator when possible.
- A note, thesis sentence, model output or prior Agent answer is not a primary source.
- Distinguish reported fact, management guidance, consensus estimate, assumption and inference.
- Supersede old facts; do not silently rewrite their history.
- Do not compare periods with different definitions without labeling the mismatch.
- If evidence is missing or conflicting, record `unverified` or `disputed`; do not fill gaps from memory.

See `contracts/research-facts.md`.

## 6. Portfolio rules

- SQLite is the structured portfolio fact source.
- Do not edit it with ad-hoc SQL. Use functions in `harness.portfolio`.
- Research conclusions must be formed before loading cost basis or P&L.
- A portfolio decision may combine research and portfolio constraints, but must state which evidence comes from which domain.
- A decision record precedes a trade record.
- Never place an order or imply execution without explicit user confirmation and external evidence.

See `contracts/portfolio-state.md`.

Retention and context-size rules are in `contracts/retention.md`. Never load a
database dump or an unbounded event history into context.

## 7. Write discipline

- Current thesis updates create a new version and then update `current.md`.
- Raw source files are immutable; corrections create a new source record.
- `summary.md` is a bounded read model, not a second full thesis.
- `facts.jsonl` contains atomic facts, not long narrative paragraphs.
- Reviews and decisions must link to the exact thesis version and fact/source IDs used.
- Never create a `legacy/` code archive. Git is the code archive; obsolete code is deleted after data migration.

## 8. Validation before completion

For material changes:

1. Validate current thesis pointers.
2. Validate fact-to-source references.
3. Confirm no forbidden context was loaded into the task artifact.
4. Run relevant tests.
5. Report unresolved evidence gaps and any migration performed.

## 9. Output language

- 面向用户的回答，以及新生成或更新的研究摘要、thesis、状态说明、事实陈述、来源说明、复盘、决策记录和组合报告，默认使用简体中文。
- 公司名称、ticker、fact/source ID、JSON 字段名、原始指标字段名、文件名及必要的专业术语可以保留英文；必要时在首次出现时补充中文解释。
- `facts.jsonl` 的 `statement` 和 `sources.json` 的 `notes` 默认使用中文；引用定位 `locator` 可保留来源中的原始英文标题、表名或章节名，以便精确核验。
- 对英文来源应使用中文转述并保留来源定位。不要为了中文化而改写成不准确的直接引语。
- 只有用户明确要求其他语言时，才切换主要输出语言。
