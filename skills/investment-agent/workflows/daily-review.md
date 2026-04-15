# Daily Review Workflow

## Goal

完成一次日常组合检查：刷新价格、记录快照、检查规则、结合 coverage 与 metadata 输出一份可归档的 daily review。

## Inputs

- `data/investment.db`
- `coverage/{SYMBOL}/current.md`
- `reviews/REVIEWS_LOG.md`
- `app/prompts/daily_review.md`

## Preferred tools

- `python app/tools/portfolio_tools.py --refresh`
- `python app/tools/pnl_tools.py --record --notes "daily"`
- `python app/tools/position_meta_tools.py read`
- `python app/tools/policy_tools.py`

## Steps

### 1. 获取组合状态

若用户接受实时价格，运行：

```bash
python app/tools/portfolio_tools.py --refresh
```

若用户只想看缓存状态，则省略 `--refresh`。

然后记录一条 P&L 快照：

```bash
python app/tools/pnl_tools.py --record --notes "daily"
```

再读取所有 position metadata：

```bash
python app/tools/position_meta_tools.py read
```

### 2. 运行 policy check

```bash
python app/tools/policy_tools.py
```

### 3. 读取 coverage thesis

对组合里的每个标的：
- 若存在 `coverage/{SYMBOL}/current.md`，解析指针并读取当前 thesis
- 提取：
  - thesis 版本与日期
  - Invalidation Conditions
  - 头寸管理原则
- 若不存在，标注为 no coverage

### 4. 生成 review 正文

输出结构以 `app/prompts/daily_review.md` 为准，至少包括：
1. Portfolio Snapshot
2. Position Breakdown
3. Policy Check
4. Attention Items
5. Dimension Summary
6. Next Action

要求：
- 不要发明工具没返回的数据
- 所有权重判断基于 USD base market value
- 对 IC 只能按可观察事实判断：TRIGGERED / WATCHING / CLEAR / UNVERIFIABLE
- 不要把成本价当作建议依据

### 5. 归档

保存到：
- `reviews/daily/YYYY-MM-DD_daily.md`
- 如冲突则 `_2.md`、`_3.md` 递增

并在 `reviews/REVIEWS_LOG.md` 追加一行：

```text
| YYYY-MM-DD | daily | reviews/daily/YYYY-MM-DD_daily.md | $总值 | daily routine | {Next Action} |
```

## Failure fallback

- 若 `portfolio_tools.py --refresh` 失败，可退回缓存状态并明确标注 price source
- 若某个 IC 需要公开数据之外的信息，标为 `UNVERIFIABLE`，不要猜
- 若无 coverage thesis，仅给出规则和仓位层面的观察，不做 thesis-driven 判断
