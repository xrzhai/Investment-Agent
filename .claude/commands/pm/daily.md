Run a complete daily portfolio review.

## Step 1 — Portfolio state

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

If the user says they don't want live prices, omit `--refresh`.

After prices are refreshed, record a P&L snapshot:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --record --notes "daily"
```

Then load position metadata (target prices, CAGR, IC status, theme tags):

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/position_meta_tools.py read
```

## Step 2 — Policy check

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/policy_tools.py
```

## Step 3 — Load coverage theses

For each position from Step 1, check `coverage/{SYMBOL}/current.md`. If it exists, read the pointer and load the thesis. Extract:
- Thesis version and date
- Invalidation Conditions (full list of IC items)
- 头寸管理原则 (target weight, add/trim conditions)

## Step 4 — Compose the review

Follow the structure in `app/prompts/daily_review.md`:

1. **Portfolio Snapshot** — total value (USD), day P&L, total P&L, position count, coverage count
   - If portfolio has CN_A positions, show: FX rate used (CNY/USD), whether stale
2. **Position Breakdown** — sorted by weight (USD-based); for each position:
   - weight%, price (in local currency), unrealized P&L (in local currency), IC status, target_base (from position_meta), expected_cagr (from position_meta), coverage status
   - For CN_A positions: show local price (CNY) and USD equivalent side by side
3. **Policy Check** — PASS or VIOLATIONS FOUND (details per violation: rule, current value, threshold, suggested action)
   - Note: all weight checks are based on USD base_market_value
4. **Attention Items** — flag any of:
   - Positions approaching weight limits
   - Positions with unrealized loss > 15%
   - **IC Assessment**: For each position with a thesis, read its Invalidation Conditions list from the thesis. Based on the current price and any recent context, make a quick judgment:
     - 🔴 TRIGGERED — condition is clearly met
     - 🟡 WATCHING — within ~20% of the threshold, or qualitative signal present
     - 🟢 CLEAR — no concern
     - If uncertain about a specific IC, flag it and note "建议运行 `/risk:ic` 确认"
   - Positions with no coverage thesis (list by name)
5. **Dimension Summary** — Do NOT list every position. Only flag positions where something notable has changed or warrants attention across Fundamental / Valuation / Technical dimensions. For each flagged position, state which dimension and what the concern is. If nothing stands out, write: "无明显异常，组合当前在 thesis 框架内运行。"
6. **Next Action** — one clear sentence

## Step 5 — Archive

Save the review to `reviews/daily/YYYY-MM-DD_daily.md` following the archive template in `app/prompts/daily_review.md`.
- If a file for today already exists, name it `YYYY-MM-DD_daily_2.md`, `_3.md`, etc.

Append one row to `reviews/REVIEWS_LOG.md`:
```
| YYYY-MM-DD | daily | reviews/daily/YYYY-MM-DD_daily.md | $总值 | daily routine | {Next Action 内容} |
```

## Cross-role nudges

- If any position lacks coverage → "Run `/researcher:status` for a prioritized coverage action list."
- If any IC looks concerning → "Run `/risk:ic` for a full Invalidation Conditions sweep."
- If policy violations exist → "Run `/pm:suggest` for specific rebalancing recommendations."

Present in clear, readable prose. Do not invent data not returned by the tools.
