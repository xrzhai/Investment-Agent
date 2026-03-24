Scan Invalidation Conditions across all covered positions and report their status.

## Step 1 — Get portfolio positions

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

## Step 2 — For each position with coverage

For each symbol where `coverage/{SYMBOL}/current.md` exists:
1. Read the current thesis (via pointer)
2. Extract the **Invalidation Conditions** section — get each IC as a discrete, assessable condition
3. Use yfinance MCP tools (`get_stock_price`, `get_stock_info`, `get_financials`) to get current data relevant to each IC
4. Assess each IC:

| Status | Meaning |
|---|---|
| 🔴 TRIGGERED | The specific condition has been met or breached |
| 🟡 WATCHING | Approaching the threshold; within ~20% of trigger level or on a clear trajectory |
| 🟢 CLEAR | Not close to triggering |

## Step 3 — Output

Group by symbol, sorted by severity (TRIGGERED first):

```
IC Sweep — {today}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NVDA  (v2, 2026-03-17)
  🟢 CLEAR   Data center revenue growth decelerates below 20% YoY — Current: +35% (FQ3 FY2026)
  🟢 CLEAR   Blackwell supply constraint extends beyond FY2026 with no revenue contribution
  🟡 WATCHING  Gross margin sustained below 70% for 2+ consecutive quarters — Current: 73.5% (↓ from 75.1%)

META  (v1, 2026-03-17)
  🟢 CLEAR   DAP growth goes negative for 2 consecutive quarters
  🟢 CLEAR   AI capex spend exceeds $70B with no monetization evidence by end of 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 0 TRIGGERED · 1 WATCHING · X CLEAR
Uncovered positions (IC not assessable): ALLW, BMNR, MSFT
```

## Step 4 — Escalation

If any IC is **TRIGGERED**:
> 🚨 **{SYMBOL}: IC TRIGGERED — "{condition text}"**
> Triggered by: {specific data point}
> Action required: Run `/researcher:update {SYMBOL}` immediately. **触发时没有台阶可下** — no deferral.

If all CLEAR:
> All tracked Invalidation Conditions are clear. Next recommended sweep: in 2 weeks or after next earnings.

## Notes

- Only assess ICs that are **observable from available data**. If an IC requires data not available via yfinance (e.g., private channel checks, specific management commentary), note it as `⚪ UNVERIFIABLE — requires manual check` rather than guessing.
- Do not conflate "stock price declined" with an IC being triggered unless the thesis explicitly uses price as an IC.
