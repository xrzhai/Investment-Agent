# Coverage Workflow

基于三维度分析框架（Fundamental / Valuation / Technical）和 Checklist 原则的持仓覆盖管理体系。

---

## 核心原则

1. **全面性优先** — 致命风险都是漏掉的，不是赌输的。分析 100 种风险哪怕 99 种落空也值得。
2. **三维度独立** — Fundamental 判断大方向；Valuation 量化 Risk/Return；Technical 观察资金流和市场结构。三者不混用，有矛盾时明确说明哪个优先及原因。
3. **错误指标第一** — Invalidation Conditions 是首要约束，不是 Risks 下的一个 bullet。触发时没有台阶可下。
4. **成本价不入决策** — avg_cost 仅用于 P&L 展示，不作为持有/减仓/退出的依据（沉没成本）。
5. **调仓必有说明** — 每次调整头寸，必须更新 thesis 并在覆盖历史中记录触发原因。

---

## 文件结构

```
coverage/
├── COVERAGE_WORKFLOW.md    ← 本文件
├── COVERAGE_LOG.md         ← 所有持仓覆盖状态一览
├── THESIS_TEMPLATE.md      ← 空白模板
│
├── NVDA/
│   ├── v1_YYYY-MM-DD.md    ← 第一版 thesis
│   ├── v2_YYYY-MM-DD.md    ← 更新版
│   └── current.md          ← 一行指针：v2_YYYY-MM-DD.md
│
└── META/
    ├── v1_YYYY-MM-DD.md
    └── current.md
```

`current.md` 仅包含一行文件名，例如：
```
v2_2026-03-17.md
```

---

## 发起覆盖（Initiate Coverage）

**触发时机：** 建仓时，或对已有仓位补建论点。

**路径 A — Skill 生成草稿：**
1. 运行 `/equity-research:thesis {SYMBOL}`，获取市场共识视角草稿
2. 对照 `THESIS_TEMPLATE.md`，将草稿改写为三维度结构
3. 重点补充：你与市场共识的分歧在哪里？你的 Invalidation Conditions 是什么？
4. 存为 `coverage/{SYMBOL}/v1_YYYY-MM-DD.md`
5. 创建 `coverage/{SYMBOL}/current.md`，写入文件名一行
6. 更新 `COVERAGE_LOG.md`

**路径 B — 直接导入：**
1. 按 `THESIS_TEMPLATE.md` 结构写作
2. 直接存为 `v1_YYYY-MM-DD.md` + `current.md`
3. 更新 `COVERAGE_LOG.md`

---

## 更新覆盖（Update Coverage）

**触发时机（人工决定）：**
- 财报发布后（尤其是 Beat/Miss 超出预期时）
- 重大产品发布 / 管理层变动 / 并购公告
- 宏观环境出现结构性变化
- 定期复盘（建议季度）
- Invalidation Condition 被触发或接近触发时

**流程：**
1. 可选：运行 `/equity-research:earnings {SYMBOL}` 获取最新数据参考
2. 复制 `current.md` 指向的当前版本，在此基础上修改
3. 保存为新版本 `vN_YYYY-MM-DD.md`（不覆盖旧版）
4. 更新 `current.md` 指针
5. 在 thesis 文件末尾的「覆盖历史」表格中记录更新摘要
6. 更新 `COVERAGE_LOG.md`

---

## Thesis 撰写 Checklist

按熊猫笔记的四个核心问题自检：

- [ ] 目前的状态是什么？（Fundamental 当前状态是否写清楚？）
- [ ] 各个维度的因子如何影响了这个状态？（三维度分析是否都覆盖到？）
- [ ] Base Scenario 和最可能的 Adverse Scenario 是什么？（是否写具体，而非泛泛而谈？）
- [ ] 什么数据变化会证明我错了？（Invalidation Conditions 是否足够具体，没有留台阶？）
- [ ] 头寸管理原则是否在开仓前就确立？（目标权重、加减仓条件、Time Horizon 是否写明？）

---

## LLM 集成逻辑

### `analyze asset {SYMBOL}`

1. 读取 `coverage/{SYMBOL}/current.md`
2. 解析指针，读取对应版本 thesis 文件
3. 注入 prompt（见 `app/prompts/asset_analysis.md`）：
   - 对照 thesis 三维度判断最新新闻的影响
   - 逐条检查 Invalidation Conditions 状态（TRIGGERED / WATCHING / CLEAR）
4. **无 thesis 时**：降级为纯新闻模式，输出末尾提示：`No coverage thesis found — consider initiating coverage.`

### `pm suggest`

1. 对每支有 coverage 的持仓：
   - 读取 thesis，将头寸管理原则注入 prompt
   - 建议需对照 thesis（大方向是否仍成立？估值是否仍合理？）
   - 建议应具体：目标权重、触发条件，而非模糊的"考虑减仓"
2. 对无 coverage 的持仓：
   - 仅基于规则（policy engine）给出建议
   - 明确标注：`[No coverage — suggestion based on rules only]`

---

## Skill 集成工作流

### Skills → Coverage 文件（更新 thesis）

| Skill | 对应触发时机 | 操作 |
| ----- | ----------- | ---- |
| `/equity-research:thesis {SYMBOL}` | 建仓 / 补建覆盖 | 生成草稿 → 按路径 A 存为 `v1_YYYY-MM-DD.md` |
| `/equity-research:earnings {SYMBOL}` | 财报后 | 生成 earnings update → 按「更新覆盖」流程出新版本 |
| `/financial-analysis:dcf {SYMBOL}` | 估值锚点更新 | 将 DCF 目标价和假设写入 thesis Valuation 节，或存为 research note |
| `/financial-analysis:comps {SYMBOL}` | 同行比较 | 将同行估值数据写入 thesis Valuation 节，或存为 research note |

### Skills → DB（持久化关键结论）

当 skill 产出的分析结论不需要更新整个 thesis，但希望在后续 review workflow 中被引用时，用 `journal research` 命令将关键结论写入数据库：

```bash
python run.py journal research NVDA --type earnings --content "Q4 FY2027 收入 $78B，超市场预期 5%；数据中心 QoQ +12%，Blackwell 需求确认；指引略低于预期，管理层归因供给约束而非需求放缓。"
```

支持的 `--type` 值：`earnings` | `dcf` | `comps` | `note`

存入后，下次运行 `python run.py analyze asset NVDA` 时，最近 3 条 research notes 会自动注入 LLM prompt。

### Python App 自动读取逻辑

- `app/services/coverage_service.py` — `load_thesis(symbol)` 读取 `coverage/{SYMBOL}/current.md` 指针 → 加载对应版本 thesis
- `recommend_engine.explain_asset(symbol)` — 有 thesis 时使用三维度结构分析；无 thesis 时降级为纯新闻模式并提示建仓
- `recommend_engine._draft_to_prompt(draft, profile)` — 对每支有 coverage 的持仓，将 Invalidation Conditions 和头寸管理原则注入 suggest prompt

---

## 数据质量与交叉验证

> **规则：凡使用来自 yfinance / 单一数据源的共识预测数据（Forward EPS、EPS 估算、目标价等），必须通过第二数据源交叉验证后才能写入 thesis。**

### 为什么需要交叉验证

yfinance 的 `eps_forward` / `pe_forward` 存在已知的**年份系统性错位**：返回值并非 FY+1E（下一财年），而通常是 **FY+2E（后年）**，导致 Forward P/E 被低估约 10–25%。

**2026-03-17 实测数据（价格基准为当日收盘）：**

| Ticker | yfinance eps_forward | 误以为 | 实际年份 | 正确 FY+1E | 1年 P/E 误差 |
|--------|---------------------|--------|---------|-----------|------------|
| GOOGL | $13.41 | FY2026E | **FY2027E** | $11.80 | 22.8x → **25.9x** |
| META | $35.88 | FY2026E | **FY2027E** | $30.19 | 17.5x → **20.8x** |
| NVDA | $10.81 | FY2027E | **FY2028E** | $8.30 | 17.0x → **22.1x** |
| TSM | $17.96 | FY2026E | **FY2027E** | ~$14.0/ADR | 18.9x → **~24.3x** |

### 必须交叉验证的数据类型

| 数据字段 | 来源 | 验证要求 |
|---------|------|---------|
| Forward EPS / Forward P/E | yfinance `eps_forward` | **必须**通过 StockAnalysis 验证年份和数值 |
| 分析师一致预期 EPS（多年） | yfinance `eps_forward` | 同上；同时确认 FY+1E / FY+2E 具体数字 |
| 分析师目标价（均值/中位数） | yfinance `target_price_mean` | 建议验证（通常准确，但有滞后） |
| 外国 ADR 估值比率（P/S, EV/EBITDA）| yfinance | **不可用**（货币混用），必须手动计算 |

### 交叉验证标准流程

**每次在 thesis Valuation 节中写入 Forward EPS / P/E 前，执行以下步骤：**

1. **获取 yfinance 数据**
   - 记录 `eps_forward`、`pe_forward`、`eps_trailing_ttm`

2. **通过 StockAnalysis 验证**（主要核查源）
   ```
   WebFetch: https://stockanalysis.com/stocks/{TICKER}/forecast/
   提取：FY+1E、FY+2E EPS 和对应财年截止日期
   ```

3. **比对并确定正确年份**
   - 计算 `当前价 / eps_forward`，与各年份 P/E 比对
   - 确认 `yfinance eps_forward` 对应哪个财年
   - 若与 FY+1E 相差 >10%，判定为年份错位，使用 StockAnalysis 数值

4. **在 thesis 中明确标注**
   - 每个 EPS 数字必须注明来源和财年：`$11.80（StockAnalysis，FY2026E）`
   - 若 yfinance 与 StockAnalysis 有小幅差异（<5%），注明"不同聚合方法"
   - Forward P/E 必须同时给出 FY+1E 和 FY+2E 两个维度

5. **若 StockAnalysis 数据不可访问**
   - 备选：`WebFetch: https://finance.yahoo.com/quote/{TICKER}/analysis/`
   - 备选：`WebSearch: "{TICKER} forward P/E 2026 2027 EPS consensus analyst"`

### 验证示例（GOOGL，2026-03-17）

```
yfinance: eps_forward = $13.41, pe_forward = 22.8x
StockAnalysis: FY2026E = $11.80, FY2027E = $13.73

比对：$305.56 / $13.41 = 22.8x ≈ FY2027 P/E (22.2x) → 年份错位，yfinance 给的是 FY2027E

结论：
- FY2026E（1年前向）= $11.80, P/E = 25.9x  ← 这才是"Forward P/E"
- FY2027E（2年前向）= $13.73, P/E = 22.2x  ← yfinance 给的是这个
```

---

## 质量控制

- Thesis 不应是市场共识的复读机。如果你的分析与卖方研究高度一致，思考：你的分歧在哪里？
- Invalidation Conditions 不应是"如果公司基本面恶化"这样的废话。应是具体的、可观察的、有时间性的条件。
- 更新 thesis 时，「覆盖历史」要诚实记录：你对了什么，错了什么，修正了什么判断。
- 定期问自己：如果现在是全新建仓而不是续持，你还会以当前权重买入吗？
