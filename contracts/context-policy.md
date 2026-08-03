# Context Policy

## Objective

Minimize context contamination while retaining enough evidence to perform the task correctly.

## Context layers

| Layer | Content | Default use |
|---|---|---|
| L0 | AGENTS, contracts, selected workflow | Every task |
| L1 | symbol status and bounded summary | Symbol and portfolio tasks |
| L2 | active structured facts and source metadata | Research and decision tasks |
| L3 | current thesis | Update, thesis review, single-symbol decision |
| L4 | targeted source excerpts | Verification only |
| L5 | archives, old reviews, old thesis versions | Explicit historical comparison only |

Load layers in order and stop when the task is supported. Never load L5 pre-emptively.

Legacy theses may contain old position-management sections. The context router
must expose a research-only view with those sections removed; the original file
remains immutable until a deliberate thesis migration creates a clean version.

## Domain isolation

### Research-only tasks

Exclude quantity, cost basis, P&L, position weight and prior trade rationale. These values create anchoring and disposition-effect risk without improving the fundamental claim.

### Portfolio review

Load portfolio state and per-symbol bounded summaries. Do not load every full thesis. Escalate only flagged symbols to a separate thesis-review task.

### Decision

Load exactly one symbol's current thesis and relevant facts, then add portfolio constraints. Keep the two evidence sections separate in the output.

## Bounded read models

`status.json` and `summary.md` are the default cross-task read models. A summary should normally remain below 1,500 Chinese characters or 1,000 English words and include:

- current thesis in one paragraph;
- thesis version and as-of date;
- 3-5 active drivers;
- 3-5 falsifiers or watch items;
- material evidence gaps;
- next review trigger.

It must not copy the complete source pack or historical narrative.

## Contamination markers

An artifact is contaminated when it:

- uses an old thesis as if current;
- treats a prior Agent conclusion as source evidence;
- mixes cost/P&L into a fundamental conclusion;
- uses facts published after the stated as-of date;
- combines two companies without an explicit comparison task;
- hides conflicting definitions or periods;
- cites a source document that was not actually inspected.
