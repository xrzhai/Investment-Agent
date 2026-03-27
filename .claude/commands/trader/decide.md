记录一笔调仓决策，生成标准格式的 decision 文件并更新 REVIEWS_LOG。

## Step 0 — 收集参数

如果参数未在调用时提供，向用户逐一询问：

- `SYMBOL` — 标的（如 000975.SZ、NVDA）
- `DIRECTION` — 方向：加仓 / 减仓 / 建仓 / 清仓
- `QTY` — 股数（正整数）
- `REF_PRICE` — 参考价（当地货币，如 ¥27.43 或 $145）
- `FUND_SOURCE` — 资金来源（如 CASH_CNY、CASH_USD）
- `REASON` — 决策理由（支持多句，自由叙述；后续整理为编号列表）
- `ALTERNATIVE`（可选）— 替代方案及为何切换，若无则跳过

## Step 1 — 读取上下文

读取以下文件，用于填充派生字段：

1. `coverage/{SYMBOL}/current.md` → 提取公司名、当前持仓数量（current_qty）、当前均价（current_avg）
2. `reviews/suggest/` 目录下最新文件（按文件名排序取最后一个）→ 提取组合总值（portfolio_total_usd）、SYMBOL 当前权重（current_weight_pct）
3. `portfolio.csv` 或从 portfolio_tools 输出 → 提取 FUND_SOURCE 当前余额（fund_balance）

若 coverage 文件不存在，继续执行但在决策摘要中标注"—（未覆盖）"。

## Step 2 — 计算派生数据

- `REF_TOTAL` = QTY × REF_PRICE（四舍五入到整数）
- 若 DIRECTION 为加仓/建仓：
  - `NEW_QTY` = current_qty + QTY
  - `NEW_CASH_APPROX` = fund_balance - REF_TOTAL
- 若 DIRECTION 为减仓：
  - `NEW_QTY` = current_qty - QTY
  - `NEW_CASH_APPROX` = fund_balance + REF_TOTAL（现金增加）
- 若 DIRECTION 为清仓：
  - `NEW_QTY` = 0
  - `NEW_CASH_APPROX` = fund_balance + REF_TOTAL
- `NEW_WEIGHT_APPROX` ≈ (NEW_QTY × REF_PRICE / FX) / portfolio_total_usd × 100%
  （A股用 CNY/USD ≈ 0.138 折算；美股直接用 USD）
  若无法计算则填"—"

## Step 3 — 确定文件名

检查 `reviews/decisions/` 目录：

- 不存在 `{YYYY-MM-DD}_decision.md` → 使用该名称
- 已存在 → 尝试 `{YYYY-MM-DD}_decision_2.md`，依此类推直到找到未占用名称

## Step 4 — 生成 decision 文件

写入 `reviews/decisions/{FILENAME}`，格式如下：

```markdown
# 调仓决策 — {DATE}

**决策时间：** {DATE}
**状态：** 待执行

---

## 决策摘要

| 项目 | 内容 |
|------|------|
| 标的 | {SYMBOL}（{公司名}） |
| 方向 | {DIRECTION} {+/-}{QTY} 股 |
| 参考价 | ¥{REF_PRICE}（或 ${REF_PRICE}） |
| 参考总额 | ¥{REF_TOTAL} CNY（或 ${REF_TOTAL} USD） |
| 资金来源 | {FUND_SOURCE}（¥{fund_balance} → ~¥{NEW_CASH_APPROX}） |
| {DIRECTION}后持仓 | {current_qty} → {NEW_QTY} 股 |
| 权重变化 | {current_weight_pct}% → ~{NEW_WEIGHT_APPROX}% |

---

## 替代方案及切换原因

{若用户提供了 ALTERNATIVE，在此填写；否则删除本节}

---

## 决策依据

{将 REASON 整理为编号列表，每条一个观点}

---

## 执行记录

> 交易执行后由 /trader:record 填写

| 项目 | 计划 | 实际 |
|------|------|------|
| 成交日期 | — | — |
| 成交价格 | ¥{REF_PRICE}（参考）| — |
| 成交股数 | {QTY} | — |
| 实际总额 | ¥{REF_TOTAL}（参考）| — |
| 新均价 | —（待用户提供）| — |
| {FUND_SOURCE} 余额 | ¥{NEW_CASH_APPROX}（参考）| — |
```

## Step 5 — 追加 REVIEWS_LOG.md

在 `reviews/REVIEWS_LOG.md` 末尾追加一行：

```
| {DATE} | decision | [{FILENAME}](decisions/{FILENAME}) | — | {REASON 第一句，截断至约30字} | {SYMBOL} {DIRECTION} {QTY}股 @ ¥{REF_PRICE} |
```

## Step 6 — 完成提示

输出：

```
✅ Decision 文件已创建：reviews/decisions/{FILENAME}
📋 REVIEWS_LOG 已更新
⏳ 状态：待执行

执行完成后请运行 /trader:record 录入实际成交数据并更新持仓。
```
