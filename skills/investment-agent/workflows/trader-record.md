# Trader Record Workflow

## Goal

在成交后更新 decision 文件状态、同步 portfolio DB 与现金余额，并记录一条执行后的 P&L 快照。

## Preferred tools

- `python app/tools/portfolio_tools.py`
- `python app/tools/portfolio_tools.py --refresh`
- `python app/tools/pnl_tools.py --record --notes ...`
- `python run.py portfolio add ...`
- `python run.py portfolio remove ...`

## Steps

### 1. 定位待执行 decision

扫描 `reviews/decisions/`：
- 只有一个待执行 → 直接用
- 多个待执行 → 让用户选择
- 没有待执行 → 停止并提示先创建 decision

### 2. 收集实际成交数据

需要：
- `EXEC_DATE`
- `EXEC_PRICE`
- `EXEC_QTY`
- `ACTUAL_TOTAL`
- `NEW_AVG_COST`
- `NEW_FUND_BALANCE`

### 3. 更新 decision 文件

- 将状态从“待执行”改为“已执行”
- 把执行记录表中的“实际”列填完整

### 4. 获取当前持仓并计算新持仓总量

先读取当前组合状态：

```bash
python app/tools/portfolio_tools.py
```

再根据方向计算：
- 加仓 / 建仓：`CURRENT_QTY + EXEC_QTY`
- 减仓：`CURRENT_QTY - EXEC_QTY`
- 清仓：`0`

### 5. 更新 DB

若不是清仓：

```bash
python run.py portfolio add {SYMBOL} {NEW_TOTAL_QTY} --cost {NEW_AVG_COST}
```

若为清仓：

```bash
python run.py portfolio remove {SYMBOL}
```

然后更新现金来源持仓：

```bash
python run.py portfolio add {FUND_SOURCE} {NEW_FUND_BALANCE} --cost {FX_RATE}
```

### 6. 刷新价格并记录快照

```bash
python app/tools/portfolio_tools.py --refresh
python app/tools/pnl_tools.py --record --notes "trade: {SYMBOL} {DIRECTION} {EXEC_QTY}@{EXEC_PRICE}"
```

### 7. 更新 REVIEWS_LOG

追加一条 executed 记录。

## Notes

- `portfolio add` 在这里应视为 upsert / set 语义
- 现金余额以用户确认值为准，不在 workflow 里擅自猜手续费
- 交易执行记录要以实际成交为准，而不是 decision 中的参考价
