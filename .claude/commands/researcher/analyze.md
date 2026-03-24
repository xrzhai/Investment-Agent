Deep-dive analysis of a single position. If no SYMBOL is provided, ask the user.

## Step 1 — Load portfolio context

Run:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

Extract for `{SYMBOL}`: quantity, avg_cost, current_price, market_value, weight_pct, unrealized_pnl, unrealized_pct.

## Step 2 — Load thesis (if exists)

Check `coverage/{SYMBOL}/current.md`.
- **Has thesis:** read the pointer, load the full thesis file. Extract Invalidation Conditions list and 头寸管理原则.
- **No thesis:** proceed in news-only mode. Flag at the end: `⚠ No coverage thesis — consider running /researcher:initiate {SYMBOL}`

## Step 3 — Detect market and fetch current data

**Detect market from symbol suffix:**

- Ends with `.SH`, `.SZ`, or `.BJ` → **CN_A** → use A-share path below
- Otherwise → **US** → use yfinance path below

### A-share data path (CN_A)

Run:

```bash
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/cn_market_data_tools.py {SYMBOL}
```

Also search via WebSearch for recent announcements, sector news, fund flows.

**Do NOT use yfinance MCP tools for CN_A fundamental data.**

### US data path

Use yfinance MCP tools to get:
- Current price, 52-week range, recent % change
- Latest news headlines (5–8 items) — categorize each as Fundamental / Valuation / Technical

**Forward P/E warning:** If presenting Forward P/E or EPS estimates, `yfinance eps_forward` has a known year-offset bug — it typically returns FY+2E, not FY+1E, making Forward P/E appear 10–25% lower than actual. Prefer validated figures already in the thesis. Do not quote `pe_forward` from yfinance directly.

## Step 4 — Output (follow `app/prompts/asset_analysis.md` structure)

**Position Facts**
| Field | Value |
|---|---|
| Shares | {quantity} |
| Current Price | ${current_price} |
| Portfolio Weight | {weight_pct}% |
| Unrealized P&L | ${unrealized_pnl} ({unrealized_pct}%) |

**Recent News** (categorized F/V/T)

**Three-Dimension Assessment**
For each dimension, state: what the thesis said → what has changed → whether the thesis still holds.
- Fundamental: [assessment]
- Valuation: [assessment]
- Technical: [assessment]

If no thesis: provide a fact-based read of each dimension without a reference frame.

**Invalidation Conditions** (thesis mode only)
For each IC listed in the thesis, assess:
- 🔴 TRIGGERED — [specific data point that triggered it]
- 🟡 WATCHING — [current value] vs threshold [X] — [distance/timeline]
- 🟢 CLEAR — [one line]

**Suggested Action**
One of: Hold / Monitor / Trim / Exit / Update thesis / Initiate coverage
Include: specific trigger condition or price level for the next decision point.

**Decision rule — 成本价不入决策:** The Suggested Action must not reference avg_cost or unrealized P&L as a rationale. Sunk costs are irrelevant. Valid inputs: thesis validity, IC status, valuation Risk/Return, position sizing principles.
