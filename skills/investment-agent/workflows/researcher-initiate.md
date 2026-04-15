# Researcher Initiate Workflow

## Goal

为一个新标的创建第一版 coverage thesis，并把关键结论写入 position metadata。

## Preconditions

- `coverage/{SYMBOL}/current.md` 不存在
- 若已存在 coverage，应改走 update workflow

## Preferred tools

- `python app/tools/portfolio_tools.py --refresh`
- `python app/tools/cn_market_data_tools.py {SYMBOL}`（A 股）
- `python app/tools/position_meta_tools.py write ...`
- `python app/tools/position_meta_tools.py read {SYMBOL}`

## Steps

### 1. Pre-flight

检查 `coverage/{SYMBOL}/current.md`：
- 存在：停止，提示改用 update workflow
- 不存在：继续

### 2. 加载持仓上下文

```bash
python app/tools/portfolio_tools.py --refresh
```

提取 `{SYMBOL}` 的：
- quantity
- avg_cost
- current_price
- market_value
- weight_pct
- unrealized_pnl
- unrealized_pct
- total_portfolio_value

若不在组合内，标记为 watchlist / potential position。

### 3. 识别市场并选择数据路径

- `.SH` / `.SZ` / `.BJ` → CN_A
- 其他 → US / global

#### CN_A

```bash
python app/tools/cn_market_data_tools.py {SYMBOL}
```

规则：
- 基本面数据优先用 JQData
- 目标价以 CNY 写入，同时可备注 USD 等值
- 市场背景关注公告、题材、资金流

#### US / global

可选择两条路径：
- consensus-first：先参考外部研究/共识，再改写成 thesis
- direct-write：直接根据已有判断撰写 thesis

### 4. 生成 thesis 初稿

严格遵循 `coverage/THESIS_TEMPLATE.md`，至少包括：
- Fundamental
- Valuation
- Technical
- Invalidation Conditions
- 头寸管理原则
- 覆盖历史（初始行）

### 5. 数据质量检查

US 标的的估值部分必须额外检查：
- `eps_forward` 需与第二数据源交叉验证
- 每个 EPS / P-E 数字标明来源与财年
- ADR 的 `ps_ratio` / `ev_ebitda` 不直接使用

### 6. 自检

至少回答：
- 当前状态是什么？
- 三维度如何影响该状态？
- Base / Adverse scenario 是什么？
- 什么变化会证明 thesis 错了？
- 头寸管理原则是否在开仓前就确立？

### 7. 保存 coverage 文件

保存为：
- `coverage/{SYMBOL}/v1_YYYY-MM-DD.md`
- `coverage/{SYMBOL}/current.md` 内容仅一行：`v1_YYYY-MM-DD.md`

并更新 `coverage/COVERAGE_LOG.md`。

### 8. 写入 position metadata

从 thesis 中提取并写入：
- bear / base / bull target
- scenario probabilities
- horizon months
- sector / region / cap-style / growth-value
- theme-tags
- risk-level
- ic-status

命令形式：

```bash
python app/tools/position_meta_tools.py write {SYMBOL} \
  --target-bear ... --target-base ... --target-bull ... \
  --prob-bear ... --prob-base ... --prob-bull ... \
  --horizon-months ... \
  --sector ... --region ... --cap-style ... \
  --growth-value ... \
  --theme-tags '[...]' \
  --risk-level ... --ic-status ...
```

然后验证：

```bash
python app/tools/position_meta_tools.py read {SYMBOL}
```
