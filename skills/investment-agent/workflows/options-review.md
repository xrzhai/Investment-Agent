# Options Review Workflow

## Goal

在日常组合检查时，把 open sold puts 当作 contingent exposure 一起回看，而不是只看现货持仓。

## Preferred tools

- `python app/tools/option_tools.py summary`
- `python app/tools/portfolio_tools.py`
- `python app/tools/policy_tools.py`

## What to inspect

### 1. Open puts

看：
- 标的
- 到期日
- strike
- premium
- reserved cash
- effective entry if assigned

### 2. Underlying context

如果可取得 underlying 现价，再看：
- `spot_price`
- `strike_gap`
- `moneyness`
- `days_to_expiry`

这些信息通常已经足够让 LLM 判断：
- 更像高概率失效
- 更像接近平值
- 更像高概率接货

### 3. Fully-assigned scenario

重点看：
- `assigned_total_shares`
- `assigned_avg_cost`
- `assigned_weight_estimate_pct`

### 4. Liquidity planning

重点看：
- `reserved_cash_by_currency`
- `cash_by_currency`
- `cash_gap_vs_reserved_by_currency`

解释原则：
- 现金缺口默认视为流动性规划信号
- 不是 automatic hard fail
- 需要结合未来工资、后续现金流与实际被行权概率理解

## Policy interpretation

当前 policy 层对 sold puts 只做两类提示：
- fully-assigned 后权重过高 -> warning
- cash gap vs reserved -> info

## Short put decision principles

对这个项目里 open sold puts 的判断，优先按下面顺序思考：

### 1. 先问：我到底愿不愿意接货？
- 如果被行权后，你仍愿意长期持有这家公司，这张 put 才是有效仓位表达。
- 如果你主观上已经不想接货，它就不再是仓位表达，而是尚未主动回收的尾部风险。

### 2. 再区分：这是概率问题，还是资金问题？
- 概率问题：`moneyness`、`strike_gap`、`days_to_expiry`
- 资金问题：真被行权时，你按 strike 需要准备多少现金；这笔钱拿不拿得出来
- 资金约束通常比 fully-assigned 报表数字更重要：
  - 拿得出来的钱，可以观察
  - 拿不出来的钱，一旦风险升温，就必须处理

### 3. 不要只看静态 fully-assigned exposure
还要一起看：
- `spot_price`
- `strike_gap`
- `moneyness`
- `days_to_expiry`
- 现在平仓要花多少钱

解释时要区分：
1. contingent exposure 仍然存在
2. 但短期 assignment probability 可能并不高
3. 是否提前平仓，取决于你是否愿意用一小笔成本买确定性

### 4. 提前平仓的触发思路
一张 put 更适合提前处理，通常是因为下面几类条件开始出现：
- 价格快速向 strike 靠近，尾部风险不再远
- 剩余时间明显缩短，不能再单靠“应该不至于”来拖延
- 你根本不想接货，而且现在还能用可接受成本把它买回来
- 若最终 assignment，需要的现金当前明确拿不出来
- 出现新的事件扰动，显著改变原来的波动判断

### 5. 当前更像哪种动作？
- 愿意接、现金可规划：更像保留 put，等待可能接货
- 愿意接、但现在还不想锁定结果：保留选择权，等更接近决策点再看
- 不愿意接、但短期风险低：可继续观察，但必须带触发条件管理
- 不愿意接、且风险开始升温：优先处理

## Notes

- 对这个项目来说，卖 put 的核心不是盯期权浮盈浮亏，而是看：
  - 你承诺了什么
  - 如果被行权，组合会变成什么样
  - 当前和未来现金流是否能承接
- suggest 可以更敏感、更偏提醒；decision 则应明确写出：为什么最终不按 suggest 做。
