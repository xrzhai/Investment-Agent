# Event Intake

## Goal

Register a new filing, earnings release, presentation, transcript or material event and decide whether it changes tracked facts or thesis.

## Steps

1. Define symbol, event type, publication time and research as-of boundary.
2. Register the source in `sources.json` before writing facts.
3. Extract atomic facts into `facts.jsonl`; label reported, guidance, consensus, assumption or inference.
4. Compare only against active facts with the same definition and period logic.
5. Classify impact:
   - `no_change`;
   - `fact_refresh`;
   - `watch_item`;
   - `thesis_update_required`;
   - `invalidation_review_required`.
6. Update `status.json` timestamps and next trigger.

For the last two classifications, finish intake and open a separate
`research_update` or `thesis_review` task. Do not expand the intake context in
place.

## Output

Create a short event note containing source IDs, fact IDs, material changes, non-comparable fields and the chosen impact classification.
