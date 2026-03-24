# Asset Analysis Prompt Template

Use this template when asked to analyse a specific holding.

---

## Instructions for Claude Code

When analysing a single asset, cover the following sections.
Fetch news with `market_data.get_news_summary(symbol)` if useful.

If a Coverage Thesis file exists at `coverage/{SYMBOL}/current.md`, read it first
and resolve the pointer to load the actual thesis version. Use the thesis to frame
all three dimensions below.

If no thesis exists, fall back to news-only mode and prompt the user at the end:
"No coverage thesis found for {SYMBOL}. Consider initiating coverage."

**Do not use cost basis (avg_cost) as a decision input — sunk cost is not relevant
to hold/trim/exit judgement. P&L figures are for context only.**

---

## Output Structure

### 1. Position Facts

- Symbol, quantity, current price, portfolio weight
- Unrealized P&L (amount and %) — display only, not a decision input

### 2. Recent News

- Key headlines (last 5, from yfinance)
- For each headline: is this Fundamental / Valuation / Technical news?
  - Fundamental: affects business model, competitive position, earnings power
  - Valuation: affects pricing expectations, analyst estimates, capital allocation
  - Technical: affects who is trading and why (flows, index events, sentiment shifts)
- Flag: does any headline touch on the Invalidation Conditions in the thesis?

### 3. Three-Dimension Assessment

*(If thesis available, assess against each thesis dimension. If not, assess from news only.)*

**Fundamental — Is the directional thesis still intact?**
- What has changed (or not changed) in the underlying business fundamentals?
- Does the Base Scenario in the thesis still hold? Any signal pointing to Adverse Scenario?

**Valuation — Has the Risk/Return profile shifted?**
- How has current pricing moved relative to the valuation anchor in the thesis?
- Is the market now pricing in more or less than before?

**Technical — Any notable change in market structure or flows?**
- Is there any sign of unusual buying/selling pressure, positioning shift, or sentiment change?
- If no thesis: note whether current price action looks consensus-driven or flow-driven

### 4. Invalidation Check

*(Only if thesis available)*
- Review each Invalidation Condition in the thesis
- State: TRIGGERED / WATCHING / CLEAR for each
- If any condition is TRIGGERED: flag prominently — no hedging, no looking for excuses

### 5. Suggested Next Step

Choose one — be specific, not hedged:
- **Hold** — thesis intact, no action
- **Monitor** — watch for [specific thing], timeframe [X weeks]
- **Consider trim** — [specific reason], suggest reducing to [X%] weight
- **Consider exit** — [which Invalidation Condition triggered], basis for exit
- **Update thesis** — significant new information warrants a thesis version update
- **Initiate coverage** — no thesis found, recommend before next review

---

## Tone Guidelines

- Separate facts from interpretation clearly
- Acknowledge uncertainty — but do not use uncertainty as an excuse to avoid a conclusion
- Never predict price direction; frame everything as Risk/Return and thesis validity
- If three dimensions conflict, say so explicitly and explain which takes precedence and why
- Do not use emojis or special Unicode symbols
