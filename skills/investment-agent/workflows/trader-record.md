# Trader Record Workflow

## Goal

在成交后更新 decision 文件状态、同步 portfolio DB 与现金余额，并记录一条执行后的 P&L 快照。

## Preferred tools

- `python app/tools/portfolio_tools.py`
- `python app/tools/portfolio_tools.py --refresh`
- `python app/tools/pnl_tools.py --record --notes ...`
- `python run.py portfolio trade ...`
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

### 4. 获取当前持仓并确认成交口径

先读取当前组合状态：

```bash
python app/tools/portfolio_tools.py
```

确认：
- `EXEC_QTY`
- `EXEC_PRICE`
- `FEES`
- `NEW_AVG_COST`（若为买入）
- `NEW_FUND_BALANCE`

### 5. 更新 DB

对标的本身，优先记录成交，而不是手工覆盖新总仓位：

```bash
python run.py portfolio trade {SYMBOL} buy {EXEC_QTY} --price {EXEC_PRICE} --fees {FEES}
```

或：

```bash
python run.py portfolio trade {SYMBOL} sell {EXEC_QTY} --price {EXEC_PRICE}
```

只有在你明确要“直接覆盖到某个绝对仓位快照”时，才使用：

```bash
python run.py portfolio add {SYMBOL} {NEW_TOTAL_QTY} --cost {NEW_AVG_COST}
```

然后再更新现金来源持仓：

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

- `portfolio trade` 是记录成交的首选接口，避免手工重算总股数
- `portfolio add` 只应视为 upsert / set 语义，用于导入或直接修正某个绝对仓位快照
- 现金余额以用户确认值为准，不在 workflow 里擅自猜手续费
- 对卖 put 收到的权利金，默认视为组合内部现金流：直接更新 `CASH_USD`，不要记成外部 `cashflow_events`
- 交易执行记录要以实际成交为准，而不是 decision 中的参考价
