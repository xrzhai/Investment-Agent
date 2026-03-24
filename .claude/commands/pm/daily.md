Run a complete daily portfolio review.

## Step 1 — Portfolio state

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

If the user says they don't want live prices, omit `--refresh`.

## Step 2 — Policy check

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/policy_tools.py
```

## Step 3 — Load coverage theses

For each position from Step 1, check `coverage/{SYMBOL}/current.md`. If it exists, read the pointer and load the thesis. Extract:
- Thesis version and date
- Invalidation Conditions (list them for status assessment)
- 头寸管理原则 (target weight, add/trim conditions)

## Step 4 — Compose the review

Follow the structure in `app/prompts/daily_review.md`:

1. **Portfolio Snapshot** — total value (USD), day P&L, total P&L, position count, coverage count
   - If portfolio has CN_A positions, show: FX rate used (CNY/USD), whether stale
2. **Position Breakdown** — sorted by weight (USD-based); for each:
   - weight%, price (in local currency), unrealized P&L (in local currency), coverage status
   - For CN_A positions: show local price (CNY) and USD equivalent side by side
3. **Policy Check** — PASS or VIOLATIONS FOUND (details per violation: rule, current value, threshold, suggested action)
   - Note: all weight checks are based on USD base_market_value
4. **Attention Items** — flag any of:
   - Positions approaching weight limits
   - Positions with unrealized loss > 15%
   - Invalidation Conditions that are WATCHING or TRIGGERED
   - Positions with no coverage thesis (list by name)
5. **Dimension Summary** — for covered positions: brief Fundamental/Valuation/Technical status vs thesis; for uncovered: note the gap
6. **Next Action** — one clear sentence

## Cross-role nudges

- If any position lacks coverage → "Run `/researcher:status` for a prioritized coverage action list."
- If any IC looks concerning → "Run `/risk:ic` for a full Invalidation Conditions sweep."
- If policy violations exist → "Run `/pm:suggest` for specific rebalancing recommendations."

Present in clear, readable prose. Do not invent data not returned by the tools.
