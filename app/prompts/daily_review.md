# Daily Review Prompt Template

Use this template to structure a daily portfolio review response.
The data comes from `portfolio_tools.py` and `policy_tools.py` outputs.

---

## Instructions for Claude Code

When conducting a daily review, present the following sections in order.
Be concise and factual. Use the investor's profile to frame the analysis.
Do not invent data — only report what the tools returned.

**Do not reference cost basis in any recommendation — sunk cost is not a
decision input. P&L figures are context, not justification.**

---

## Output Structure

### 1. Portfolio Snapshot

- Total market value
- Overall unrealized P&L (amount and %)
- Number of positions / number with active coverage thesis
- Note whether prices are live (refreshed) or cached

### 2. Position Breakdown

For each position (sorted by weight, largest first):
- Symbol, current price, market value, portfolio weight %
- Unrealized P&L (amount and %)
- Coverage status: [Active thesis vN] or [No coverage]

### 3. Policy Check

- State clearly: PASS or VIOLATIONS FOUND
- If violations exist, list each one with:
  - What rule was triggered
  - Current value vs threshold
  - Suggested action

### 4. Attention Items

Flag any of the following:
- Positions approaching or exceeding weight limits
- Positions with unrealized loss > 15% — prompt: does this touch Invalidation Conditions?
- Positions with no coverage thesis — prompt to initiate
- Any forbidden symbols

### 5. Dimension Summary (Portfolio Level)

A brief read on the portfolio across the three dimensions:

- **Fundamental**: Overall, are the businesses in this portfolio on track?
  (Only flag if there is something concrete to note — not a generic comment)
- **Valuation**: Is the overall portfolio pricing reasonable given current weights?
  Flag positions that look stretched or unusually cheap vs their thesis anchors.
- **Technical**: Any notable market structure observations across the holdings?

### 6. Next Action

One clear sentence on what needs attention today, if anything.
If everything is within bounds, say so plainly.

---

## Tone Guidelines

- Factual and neutral — no hype, no alarm unless warranted
- Reference the investor's own rules and thesis when flagging issues
- If three dimensions conflict on a position, note it — do not paper over it
- Do not use emojis or special Unicode symbols
