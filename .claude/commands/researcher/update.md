Update existing coverage for a position. If no SYMBOL is provided, ask the user.

## Pre-flight check

1. Check if `coverage/{SYMBOL}/current.md` exists.
   - **If it does not exist** → stop. Tell the user there is no coverage yet and suggest `/researcher:initiate {SYMBOL}` instead.
   - **If it exists** → read the pointer (single filename on line 1), load `coverage/{SYMBOL}/{filename}` as the current thesis.

## Step 1 — Identify trigger

Ask the user what triggered this update (if not provided as argument):
- `earnings` — post-earnings review
- `event` — product launch, management change, M&A, macro shift
- `quarterly` — scheduled quarterly review
- `ic` — Invalidation Condition triggered or approaching threshold
- `other` — describe briefly

## Step 2 — Load fresh context

Run:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

Optionally suggest: "Run `/equity-research:earnings {SYMBOL}` for fresh data." Especially important for `earnings` trigger, but useful for any update touching valuation or fundamentals.

**Data quality reminder:** If this update touches Valuation or Forward P/E numbers, the yfinance `eps_forward` year-offset bug applies — see `/researcher:initiate` for the full procedure. Key rule: cross-check via `WebFetch https://stockanalysis.com/stocks/{SYMBOL}/forecast/` and label every EPS number with source and fiscal year. For foreign ADRs: do not use yfinance `ps_ratio` or `ev_ebitda`.

## Step 3 — Generate update draft

Starting from the current thesis, review and update each section where the evidence has changed:

**Mandatory review checklist:**
- [ ] Which Invalidation Conditions changed status? (TRIGGERED / WATCHING / CLEAR)
- [ ] Has the fundamental direction (bull thesis) been confirmed, weakened, or broken?
- [ ] Does the valuation still offer acceptable risk/return? Update price targets if needed.
- [ ] Has the technical picture changed materially?
- [ ] Does the position sizing still make sense at current weight? Update 头寸管理原则.

**Do NOT change sections where nothing has materially changed.** An update that rewrites everything with no new evidence is noise.

**覆盖历史 — append a new row (be honest):**
```
| vN | {today} | {trigger} | What changed: what you got right, what you got wrong, what judgment you revised |
```

## Step 3.5 — Thesis self-check (Panda Notes)

Verify points relevant to sections you changed. Flag any that the current update leaves incomplete:

- [ ] 目前的状态是什么？（Fundamental 当前状态是否写清楚？）
- [ ] 各个维度的因子如何影响了这个状态？（三维度分析是否都覆盖到？）
- [ ] Base Scenario 和最可能的 Adverse Scenario 是什么？（是否写具体，而非泛泛而谈？）
- [ ] 什么数据变化会证明我错了？（Invalidation Conditions 是否足够具体，没有留台阶？）
- [ ] 头寸管理原则是否在开仓前就确立？（目标权重、加减仓条件、Time Horizon 是否写明？）

**Quality control — honest coverage history:**

- The 覆盖历史 row must state what you got right, what you got wrong, and what judgment you revised. "Updated valuation" is not sufficient.
- Ask: if starting fresh today, would you buy at current weight?

## Step 4 — Save instructions

Remind the user to:
1. Save as `coverage/{SYMBOL}/v{N}_{YYYY-MM-DD}.md` (increment N; do NOT overwrite the old version)
2. Update `coverage/{SYMBOL}/current.md` to contain the new filename
3. Update `coverage/COVERAGE_LOG.md` — change the version and trigger columns for this symbol

**Data quality rules still apply on any updated valuation numbers.** See `/researcher:initiate` for the Forward EPS cross-validation procedure.

## Step 5 — Update position metadata in DB

After saving the updated thesis, refresh the stored metadata. Only update fields where the thesis has materially changed. Run:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/position_meta_tools.py write {SYMBOL} \
  --target-bear {BEAR_PRICE} --target-base {BASE_PRICE} --target-bull {BULL_PRICE} \
  --prob-bear {P_BEAR} --prob-base {P_BASE} --prob-bull {P_BULL} \
  --horizon-months {MONTHS} \
  --sector "{SECTOR}" --region {REGION} --cap-style {CAP} \
  --growth-value {GROWTH_VALUE} \
  --theme-tags '{THEME_JSON}' \
  --risk-level {RISK} --ic-status {IC_STATUS}
```

**Fields to always update after any thesis revision:**
- `--ic-status`: reflect the current IC status as of this update (CLEAR / WATCHING / TRIGGERED)
- `--target-bear/base/bull` and `--prob-bear/base/bull`: update if valuation scenarios changed
- `--theme-tags`: update if the investment thesis or macro exposure has shifted
- Other fields (sector, region, cap-style, growth-value): only update if materially changed

**Extraction rules** (same as `/researcher:initiate` Step 5):
- `--target-bear/base/bull`: 估值分析 → 各场景的 12-24 个月目标价
- `--prob-bear/base/bull`: 场景概率权重，三者之和必须等于 1.0
- `--horizon-months`: 头寸管理原则 → Time Horizon（"18-24 个月" 取中值 21）
- `--theme-tags`: JSON 数组，2-4 个关键词，核心投资主题和宏观因子暴露
- `--ic-status`: 若任一 IC = TRIGGERED → TRIGGERED；有 WATCHING → WATCHING；否则 CLEAR

确认更新是否成功：

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/position_meta_tools.py read {SYMBOL}
```
