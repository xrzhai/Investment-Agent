交易执行完成后录入实际成交数据，更新 decision 文件状态、portfolio DB 持仓与现金，并记录 P&L 快照。

## Step 0 — 定位待执行 decision 文件

扫描 `reviews/decisions/` 目录下所有 `*_decision*.md` 文件，读取每个文件的 `**状态：**` 字段：

- **只有一个"待执行"** → 自动使用，告知用户文件路径
- **多个"待执行"** → 列出让用户选择
- **无"待执行"** → 提示："没有找到待执行的决策文件，请先运行 /trader:decide"，停止执行

从选定文件中提取：
- `SYMBOL`（从决策摘要表的"标的"行）
- `DIRECTION`（加仓 / 减仓 / 建仓 / 清仓）
- `PLAN_QTY`（计划股数）
- `REF_PRICE`（参考价）
- `FUND_SOURCE`（资金来源，如 CASH_CNY）
- `DECISION_FILENAME`（文件名）

## Step 1 — 收集实际成交数据

向用户询问（若在调用参数中已提供则跳过）：

- `EXEC_DATE` — 成交日期（默认今天 {YYYY-MM-DD}）
- `EXEC_PRICE` — 实际成交价（每股，当地货币）
- `EXEC_QTY` — 实际成交股数（若与计划相同则确认，若不同则记录差异）
- `ACTUAL_TOTAL` — 实际总耗费（CNY 或 USD，含所有手续费印花税）
- `NEW_AVG_COST` — 新持仓均价（由用户根据税费自行计算后提供）
- `NEW_FUND_BALANCE` — {FUND_SOURCE} 成交后余额（用户提供，直接填入）

## Step 2 — 更新 decision 文件

**2a. 修改状态行：**

将文件中 `**状态：** 待执行` 替换为 `**状态：** 已执行`

**2b. 填写执行记录表的"实际"列：**

找到执行记录表，逐行填入实际值：

| 项目 | 计划 | 实际 |
|------|------|------|
| 成交日期 | — | {EXEC_DATE} |
| 成交价格 | ¥{REF_PRICE}（参考）| ¥{EXEC_PRICE} |
| 成交股数 | {PLAN_QTY} | {EXEC_QTY} |
| 实际总额 | ¥...（参考）| ¥{ACTUAL_TOTAL} |
| 新均价 | —（待用户提供）| ¥{NEW_AVG_COST} |
| {FUND_SOURCE} 余额 | ¥...（参考）| ¥{NEW_FUND_BALANCE} |

## Step 3 — 读取当前持仓数量

运行：

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py
```

从输出中找到 SYMBOL 当前 quantity（`CURRENT_QTY`）。

若 DIRECTION = 清仓，跳过此步，`NEW_TOTAL_QTY` = 0。

## Step 4 — 计算新持仓总量

- 加仓 / 建仓：`NEW_TOTAL_QTY` = CURRENT_QTY + EXEC_QTY
- 减仓：`NEW_TOTAL_QTY` = CURRENT_QTY - EXEC_QTY
- 清仓：`NEW_TOTAL_QTY` = 0

## Step 5 — 更新 DB

**5a. 更新持仓：**

若 DIRECTION ≠ 清仓：
```
/c/Users/zhaix/miniconda3/envs/work/python.exe run.py portfolio add {SYMBOL} {NEW_TOTAL_QTY} --cost {NEW_AVG_COST}
```

若 DIRECTION = 清仓：
```
/c/Users/zhaix/miniconda3/envs/work/python.exe run.py portfolio remove {SYMBOL}
```

**5b. 更新现金余额（FUND_SOURCE）：**

CASH_CNY 使用汇率 0.1377，CASH_USD 使用 1.0（或当前市场汇率，若用户提供）：
```
/c/Users/zhaix/miniconda3/envs/work/python.exe run.py portfolio add {FUND_SOURCE} {NEW_FUND_BALANCE} --cost {FX_RATE}
```

> 注：`portfolio add` 是 SET 语义（upsert），直接传入新总量即可，无需手动做加减法。

## Step 6 — 刷新价格 + 记录 P&L 快照

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py --refresh
```

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --record --notes "trade: {SYMBOL} {DIRECTION} {EXEC_QTY}@{EXEC_PRICE}"
```

## Step 7 — 追加 REVIEWS_LOG.md

在 `reviews/REVIEWS_LOG.md` 末尾追加一行：

```
| {EXEC_DATE} | executed | [{DECISION_FILENAME}](decisions/{DECISION_FILENAME}) | — | {SYMBOL} 成交 @ ¥{EXEC_PRICE} | 实际 {DIRECTION} {EXEC_QTY}股，新均价¥{NEW_AVG_COST}，{FUND_SOURCE}→¥{NEW_FUND_BALANCE} |
```

## Step 8 — 完成提示

输出执行摘要：

```
✅ 执行记录完成

标的：{SYMBOL}  {DIRECTION} {EXEC_QTY}股
成交价：¥{EXEC_PRICE}  实际总耗费：¥{ACTUAL_TOTAL}
新均价：¥{NEW_AVG_COST}
新持仓：{NEW_TOTAL_QTY} 股
{FUND_SOURCE}：¥{NEW_FUND_BALANCE}

DB 已更新 ✓  P&L 快照已记录 ✓  REVIEWS_LOG 已更新 ✓
```
