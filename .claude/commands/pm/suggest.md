Generate actionable position recommendations grounded in portfolio-level structure and per-stock risk/return data.

## Step 0 — Coverage & metadata gate

Run:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

For each position, check if `coverage/{SYMBOL}/current.md` exists.

**If any position lacks coverage → STOP.** Output:

```
⛔ suggest 无法运行：以下标的缺少覆盖报告：
  - {SYMBOL} → 请先运行 /researcher:initiate {SYMBOL}

建立所有覆盖后重新运行 /pm:suggest。
```

Also run:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/position_meta_tools.py read
```

If any position has `meta_updated_at` = null or older than 30 days, **warn** (do not stop):

```
⚠️ 以下标的 metadata 可能过时，建议更新后再运行 suggest：
  - {SYMBOL}（上次更新：{DATE}）→ 运行 /researcher:update {SYMBOL}
```

## Step 1 — Load full portfolio state

From the `position_meta_tools.py read` output above, build a working table for all positions:

| Field | Source |
|-------|--------|
| symbol, weight_pct, current_price | portfolio_tools output |
| expected_cagr, target_base, risk_level, ic_status | position_meta read output |
| theme_tags, region, sector, growth_value | position_meta read output |

## Step 2 — Policy check

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/policy_tools.py
```

Note any violations — these are **hard constraints** that override other recommendations.

## Step 3 — Load investment principles

Read `config/principles.md` if it exists. Use these to frame every recommendation:
- **选股原则**: does each position still fit the stock selection criteria?
- **组合原则**: concentration, hedge logic, return/vol balance
- **调仓/离场原则**: cross-reference with position management rules in each thesis

If `principles.md` is missing or all sections marked "（待填写）", proceed without it.

## Step 4 — Portfolio-level diagnosis

Present this section first, before any individual stock recommendations.

### 4a. Thematic exposure (主题敞口)

Group positions by `theme_tags`. Use semantic judgment to cluster related tags — e.g. "AI基础设施", "AI芯片", "CUDA生态", "数据中心" are the same cluster. For each cluster:

- List member positions and their weights
- Show combined weight %
- Flag: **≥35% → ⚠️ 过重** | 20–35% → ✓ 合理 | <20% → ℹ️

Example output:

```
主题敞口分析
─────────────────────────────────────────────────
AI 核心敞口   NVDA 22% + TSM 14% + GOOGL 12% = 48%  ⚠️ 过重（建议 ≤35%）
中国敞口      PDD 5% + ALLW 8% = 13%                ✓ 合理
流动性/加密    BTC 12%                               ✓ 合理
消费互联网     META 18% + NFLX 5% = 23%              ✓ 合理
─────────────────────────────────────────────────
```

### 4b. Regional exposure (地区敞口)

Summarise by `region` field: US / China / Crypto / TW / Other — combined weight % each.

### 4c. Style snapshot

- Growth / Value / Blend distribution across portfolio
- Cap concentration (mega-cap heavy?)
- Consistency with profile `style: quality_growth`

### 4d. IC risk summary

```
IC 状态汇总：CLEAR {N} | WATCHING {N} | TRIGGERED {N}
```

Any TRIGGERED IC → immediate action flag at the top of the per-stock section.

## Step 5 — Per-stock recommendations

For each position, load `coverage/{SYMBOL}/current.md` → extract 头寸管理原则 (target weight, add/trim/exit conditions).

Sort order within each risk tier: highest `expected_cagr` first.

Present each position as:

```
NVDA  |  weight 22% → target 20%  |  CAGR +28% (高风险)  |  IC: CLEAR
推荐: TRIM ~2%
理由: 超目标权重 +2%；AI主题敞口已达 48%（⚠️ 过重），NVDA 是最大贡献者
Thesis rule: trim on any rally above $950（来自头寸管理原则）

META  |  weight 18% → target 18%  |  CAGR +22% (中风险)  |  IC: CLEAR
推荐: HOLD
理由: 权重在目标范围内；消费互联网敞口 23%（合理）；CAGR 性价比最高
Thesis rule: add below $580 if core ads revenue growth re-accelerates
```

**Recommendation decision logic (apply in priority order):**

1. IC = TRIGGERED → EXIT or significant TRIM per thesis exit conditions
2. Policy violation → trade to resolve it (hard constraint)
3. weight > target + 3% AND theme cluster ⚠️ 过重 → TRIM
4. weight < target − 3% AND CAGR top-tercile AND IC = CLEAR → ADD consideration
5. Otherwise → HOLD

For positions with no CAGR data (null `expected_cagr`): note "CAGR 数据缺失，建议先运行 /researcher:update" and default to HOLD unless a policy or IC rule triggers.

## Step 6 — Summary

End with:

- **Priority action**: one sentence — the single most important trade or action today
- **Risk alerts**: any theme overweight, WATCHING or TRIGGERED ICs
- **Best opportunity**: the position with highest risk-adjusted CAGR that is currently underweight vs. target
- *These suggestions are advisory. Final decisions require your judgment against the full thesis.*

## Step 7 — Archive output

After completing Step 6, save the full output to:

```
reviews/suggest/{YYYY-MM-DD}_suggest.md
```

If a file with that name already exists (same-day re-run), append `_2`, `_3`, etc.

**File format** — use this exact structure:

```markdown
# Portfolio Suggest — {YYYY-MM-DD}

**组合总值：** ${total_value}
**运行时间：** {DATETIME}
**触发原因：** {ask user for one line, e.g. "季度整理" / "财报后复盘" / "新 metadata 写入"}

---

## 优先行动（Priority Action）
{one sentence from Step 6}

## 风险警示（Risk Alerts）
{bullet list from Step 6}

## 最佳机会（Best Opportunity）
{one sentence from Step 6}

---

## 组合诊断
{Step 4 output: 主题敞口表 + 地区敞口表 + 风格/IC 汇总}

---

## 个股建议

| Symbol | 当前权重 | 目标权重 | CAGR | Risk | IC | 建议 | 理由摘要 |
|--------|---------|---------|------|------|----|------|---------|
{one row per position from Step 5}

---

## 数据快照（存档时刻）

| Symbol | Price | Weight% | Bear | Base | Bull | P(Bear/Base/Bull) | CAGR% | meta_updated |
|--------|------:|--------:|-----:|-----:|-----:|-------------------|------:|-------------|
{one row per position — all values at time of run}

---

## 执行跟踪

> 本次建议中的操作，后续执行后在此记录

| 标的 | 建议 | 执行日期 | 实际操作 | 备注 |
|------|------|---------|---------|------|
{rows for TRIM/ADD actions only; HOLD positions omit}
```

**Also append one line to `reviews/REVIEWS_LOG.md`:**

```markdown
| {YYYY-MM-DD} | suggest | [{FILENAME}](suggest/{FILENAME}) | ${total_value} | {trigger} | {priority_action_one_line} |
```

Ask the user for the trigger reason before writing. If they say skip, use "—".
