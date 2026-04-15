# Trader Decide Workflow

## Goal

记录一笔尚未执行的调仓决策，生成标准 decision 文件，并追加到 `reviews/REVIEWS_LOG.md`。

## Required inputs

- `SYMBOL`
- `DIRECTION`：加仓 / 减仓 / 建仓 / 清仓
- `QTY`
- `REF_PRICE`
- `FUND_SOURCE`
- `REASON`
- `ALTERNATIVE`（可选）

## Steps

### 1. 收集参数

若缺少输入，先补齐。

### 2. 读取上下文

优先读取：
- `coverage/{SYMBOL}/current.md`
- `reviews/suggest/` 中最新建议文件
- 当前组合状态 / 资金来源余额

若 coverage 不存在，继续执行，但在摘要里标注未覆盖。

### 3. 计算派生字段

至少计算：
- `REF_TOTAL = QTY × REF_PRICE`
- `NEW_QTY`
- `NEW_CASH_APPROX`
- `NEW_WEIGHT_APPROX`（能算则算，不能算则留空）

### 4. 选择 decision 文件名

在 `reviews/decisions/` 下按日期生成：
- `YYYY-MM-DD_decision.md`
- 若冲突则 `_2.md`、`_3.md`

### 5. 写 decision 文件

文件需包含：
- 决策时间
- 状态：待执行
- 决策摘要表
- 替代方案及切换原因（若有）
- 决策依据
- 执行记录占位表

### 6. 追加 REVIEWS_LOG

在 `reviews/REVIEWS_LOG.md` 追加一条 decision 记录。

## Notes

- 决策文件是“计划与理由”的归档，不是成交回执
- 实际成交完成后，再走 `trader-record.md`
