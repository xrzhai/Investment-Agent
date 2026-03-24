Show coverage status across the entire portfolio.

## Steps

1. **Read `coverage/COVERAGE_LOG.md`** — load the current log table.

2. **Get portfolio positions**:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py
```
(No `--refresh` — this is a status check, not a price refresh.)

3. **For each position in the portfolio**, check `coverage/{SYMBOL}/current.md`:
   - If exists: read the pointer filename to extract version number and date (format: `vN_YYYY-MM-DD.md`)
   - If missing: mark as `[NO COVERAGE]`

4. **Output the status table**:

```
Coverage Status — {today}
────────────────────────────────────────────────────────────
Symbol  Weight%  Version  Last Updated  Age(days)  Status
NVDA    22.4%    v2       2026-03-17    1          ✅ Current
META    18.1%    v1       2026-03-17    1          ✅ Current
GOOGL   15.2%    v1       2026-03-17    1          ✅ Current
TSM     12.8%    v1       2026-03-17    1          ✅ Current
ALLW    8.3%     —        —             —          ⚠ NO COVERAGE
BMNR    4.1%     —        —             —          ⚠ NO COVERAGE
────────────────────────────────────────────────────────────
Coverage: 4/6 positions (67%)
Needs attention: 2 positions without coverage
```

5. **Flag positions needing attention**:
   - `⚠ NO COVERAGE` — no thesis at all
   - `⚠ STALE (>90 days)` — last update older than 90 days
   - `⚠ CHECK IC` — if COVERAGE_LOG shows a triggered/watching event (read from log comments)

6. **End with a prioritized action list** (max 3 items), e.g.:
   - "1. Run `/researcher:initiate ALLW` — 8.3% weight, no coverage"
   - "2. Run `/researcher:initiate BMNR` — 4.1% weight, no coverage"
