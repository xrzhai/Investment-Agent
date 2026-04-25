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

## Notes

- 对这个项目来说，卖 put 的核心不是盯期权浮盈浮亏，而是看：
  - 你承诺了什么
  - 如果被行权，组合会变成什么样
  - 当前和未来现金流是否能承接
