Initiate coverage for a new position. If no SYMBOL is provided, ask the user.

## Pre-flight check

1. Check if `coverage/{SYMBOL}/current.md` exists.
   - **If it exists** → stop. Tell the user coverage already exists and suggest `/researcher:update {SYMBOL}` instead.
   - **If it does not exist** → proceed.

## Step 1 — Load portfolio context

Run:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

Extract for `{SYMBOL}`: `quantity`, `avg_cost`, `current_price`, `market_value`, `weight_pct`, `unrealized_pnl`, `unrealized_pct`, `total_portfolio_value`.

If the symbol is not in the portfolio, note it as a **watchlist / potential position** and skip the holdings block.

## Step 2 — Detect market and choose data path

**Detect market from symbol suffix:**

- Symbol ends with `.SH`, `.SZ`, or `.BJ` → **market = CN_A** → use A-share data path below
- Otherwise → **market = US** → use US data path below

---

### A-share data path (CN_A)

Run the A-share data tool to get price + fundamentals:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/cn_market_data_tools.py {SYMBOL}
```

This returns: current price (CNY), P/E, P/B, ROE, revenue growth, net profit margin, etc. from JQData.

Also search for market context via WebSearch:

- Search: `{SYMBOL} 贵州茅台 最新 公告 题材 机构 2025` (replace company name)
- Search: `{SYMBOL} 行业 竞争格局 2025`

**Do NOT use yfinance MCP tools for CN_A fundamental data** — data quality is unreliable for A-shares.

**A-share data quality rules:**

- All financial metrics (P/E, P/B, ROE, revenue) should come from JQData output above
- Price targets should be in CNY. In the thesis, also note USD equivalent at current FX rate.
- "Market context" for A-shares = 公告 (announcements) + 题材 (themes) + 资金流 (fund flows) — not direct equivalents of US news flow

**Path B — Direct write:**
If the user already has a thesis in mind, skip to Step 3 with the data collected above.

---

### US data path (market = US)

**Path A — Consensus-first (recommended):**
Ask the user: "Run `/equity-research:thesis {SYMBOL}` for a market consensus starting point?"
If yes, run it and use the output as raw material for Step 3.

**Path B — Direct write:**
If the user already has a thesis in mind, skip the consensus draft and proceed directly to Step 3.

## Step 3 — Generate thesis draft

Follow `coverage/THESIS_TEMPLATE.md` exactly. Structure:

- **Fundamental（大方向）** — Current state, key drivers, bull/bear case
- **Valuation（Risk/Return）** — Multiples, scenarios, upside/downside targets
- **Technical（资金流与市场结构）** — Price structure, flows, positioning
- **Invalidation Conditions** — Concrete, observable, time-bounded triggers (NOT "if fundamentals deteriorate")
- **头寸管理原则** — Fill with actual numbers from Step 1: current weight, target weight, add/trim/exit conditions anchored to actual price
- **覆盖历史** — First entry only: `| v1 | {today} | 建仓初始覆盖 | — |`

### Data quality rules — US stocks (MANDATORY)

**Forward EPS / Forward P/E:**
`yfinance eps_forward` has a known systematic year-offset bug — it typically returns FY+2E, not FY+1E, causing Forward P/E to be understated by ~10–25%.

Before writing any Forward EPS or P/E into the thesis:
1. Get `eps_forward` from yfinance MCP (`get_stock_info`)
2. Fetch from StockAnalysis: `WebFetch https://stockanalysis.com/stocks/{SYMBOL}/forecast/`
3. Compare: compute `current_price / eps_forward`. If it matches FY+2 P/E rather than FY+1 P/E, the data is offset.
4. Use StockAnalysis values. Label every number with source and fiscal year: `$11.80 (StockAnalysis, FY2026E)`
5. Always show both FY+1E and FY+2E P/E.

**Foreign ADRs (TSM, etc.):** `ps_ratio` and `ev_ebitda` from yfinance are corrupted by currency mixing. Do not use them. Calculate manually or omit.

**Analyst target prices:** Generally usable but may lag; note the date.

## Step 3.5 — Thesis self-check (Panda Notes)

Before moving to Step 4, verify all five points:

- [ ] 目前的状态是什么？（Fundamental 当前状态是否写清楚？）
- [ ] 各个维度的因子如何影响了这个状态？（三维度分析是否都覆盖到？）
- [ ] Base Scenario 和最可能的 Adverse Scenario 是什么？（是否写具体，而非泛泛而谈？）
- [ ] 什么数据变化会证明我错了？（Invalidation Conditions 是否足够具体，没有留台阶？）
- [ ] 头寸管理原则是否在开仓前就确立？（目标权重、加减仓条件、Time Horizon 是否写明？）

**Quality control:**

- If the thesis reads like a sell-side summary, ask: where is your divergence from market consensus?
- ICs must be concrete, observable, and time-bounded — "if fundamentals deteriorate" is not an IC.

## Step 4 — Save instructions

Remind the user to:
1. Save as `coverage/{SYMBOL}/v1_{YYYY-MM-DD}.md`
2. Create `coverage/{SYMBOL}/current.md` containing exactly one line: `v1_{YYYY-MM-DD}.md`
3. Add a row to `coverage/COVERAGE_LOG.md`:
   `| {SYMBOL} | {today} | v1_{YYYY-MM-DD}.md | 建仓初始覆盖 | Active |`

Do not invent portfolio data not returned by the tools. If `portfolio_tools.py` fails, fall back to `portfolio.csv` for quantity/avg_cost and yfinance MCP for current price.

## Step 5 — Write position metadata to DB

From the completed thesis, extract the values below and run (replace all `{...}` placeholders with actual numbers):

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

**Extraction rules:**
- `--target-bear/base/bull`: 估值分析 → 各场景的 12-24 个月目标价（单位：与 current_price 相同的货币）
- `--prob-bear/base/bull`: 场景概率权重，三者之和必须等于 1.0
- `--horizon-months`: 头寸管理原则 → Time Horizon（写 "18-24 个月" 取中值 21；"1 年" 写 12）
- `--sector`: 行业分类，英文（如 Technology / Consumer Discretionary / Financial Services）
- `--region`: 实际业务地区（US / China / TW / Crypto），非上市地
- `--cap-style`: mega（>2000亿美元市值）/ large（200-2000亿）/ mid（20-200亿）/ small（<20亿）
- `--growth-value`: growth / value / blend
- `--theme-tags`: JSON 数组，2-4 个关键词，代表该标的的核心投资主题和宏观因子暴露。例：
  - NVDA → `["AI基础设施","CUDA生态","数据中心"]`
  - TSM → `["AI芯片","半导体代工","台海地缘"]`
  - BTC → `["加密资产","流动性","风险偏好"]`
  - PDD → `["中国电商","消费降级","跨境电商"]`
- `--risk-level`: 综合判断（low / medium / high）。参考：单标的波动率大、IC 接近触发、地缘政治敞口大 → high
- `--ic-status`: 当前 IC 整体状态。若任一 IC = TRIGGERED → TRIGGERED；有 WATCHING → WATCHING；否则 CLEAR

确认写入是否成功：

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/position_meta_tools.py read {SYMBOL}
```

检查 `expected_cagr_pct` 是否合理（与手动心算接近），`theme_tags` 是否正确。
