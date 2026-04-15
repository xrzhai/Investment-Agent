# Daily Review Prompt Template

Use this template to structure a daily portfolio review response.
The data comes from `portfolio_tools.py`, `position_meta_tools.py`, and `policy_tools.py` outputs.

---

## Instructions for the agent

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

| Symbol | Weight | Price | P&L | IC | Target | CAGR |
|--------|--------|-------|-----|----|--------|------|

- **Symbol**: ticker (for CN_A, show local price in CNY and USD equivalent side by side)
- **Weight**: % of total portfolio (USD-based)
- **Price**: current price in local currency
- **P&L**: unrealized P&L in local currency (amount and %)
- **IC**: IC status from the quick assessment — 🔴 TRIGGERED / 🟡 WATCHING / 🟢 CLEAR / — (no coverage)
- **Target**: target_base price from position_meta (local currency); show — if not available
- **CAGR**: expected_cagr from position_meta; show — if not available
- **Coverage**: [Active thesis vN] or [No coverage]

### 3. Policy Check

- State clearly: PASS or VIOLATIONS FOUND
- If violations exist, list each one with:
  - What rule was triggered
  - Current value vs threshold
  - Suggested action

### 4. Attention Items

Flag any of the following:

- Positions approaching or exceeding weight limits
- Positions with unrealized loss > 15% — does this touch Invalidation Conditions?
- IC status 🔴 TRIGGERED or 🟡 WATCHING — list the specific IC item and why it is flagged
- Positions with no coverage thesis — prompt to initiate

### 5. Dimension Summary

**Do not list every position.** Only flag positions where something notable has changed
or warrants attention in the Fundamental / Valuation / Technical dimensions.

Format for each flagged position:
> `{SYMBOL}: {Dimension} — {one-sentence description of what changed or why it warrants attention}`

If nothing stands out across the portfolio, write:
> "无明显异常，组合当前在 thesis 框架内运行。"

### 6. Next Action

One clear sentence on what needs attention today, if anything.
If everything is within bounds, say so plainly.

---

## Tone Guidelines

- Factual and neutral — no hype, no alarm unless warranted
- Reference the investor's own rules and thesis when flagging issues
- If three dimensions conflict on a position, note it — do not paper over it
- Do not use emojis except for IC status indicators (🔴 🟡 🟢)

---

## Archive Template

After presenting the review to the user, save the following to
`reviews/daily/YYYY-MM-DD_daily.md` (use `_2.md`, `_3.md` if the date file already exists).

```markdown
# Portfolio Daily — YYYY-MM-DD

**组合总值:** $XXX,XXX
**运行时间:** YYYY-MM-DDTHH:MM:SS
**触发原因:** daily routine

---

## Next Action

[一句话]

---

## 注意事项 (Attention Items)

[Bullet list. 无则写"无。"]

---

## Dimension 异常

[仅列异常项，格式：SYMBOL: 维度 — 描述。无则写"无。"]

---

## 持仓明细

| Symbol | Weight | Price | P&L | IC | Target | CAGR | Coverage |
|--------|--------|-------|-----|----|--------|------|----------|

---

## Policy Check

[PASS 或 VIOLATIONS: 逐条列出]

---

## 数据快照

[记录归档时刻的持仓价格、总值。从 portfolio_tools.py 输出直接摘录关键字段。]
```

Then append one row to `reviews/REVIEWS_LOG.md`:

```
| YYYY-MM-DD | daily | reviews/daily/YYYY-MM-DD_daily.md | $总值 | daily routine | {Next Action 内容} |
```
