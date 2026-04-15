# Researcher Analyze Workflow

## Goal

对单个持仓做深度分析，结合 thesis、最新市场数据与新闻，判断 thesis 当前是否仍成立。

## Preferred tools

```bash
python app/tools/portfolio_tools.py --refresh
python app/tools/cn_market_data_tools.py {SYMBOL}   # A 股时
```

以及：
- `coverage/{SYMBOL}/current.md`
- `app/prompts/asset_analysis.md`

## Steps

### 1. 加载持仓上下文

```bash
python app/tools/portfolio_tools.py --refresh
```

提取：
- quantity
- current_price
- weight_pct
- unrealized_pnl
- unrealized_pct

### 2. 加载 thesis（如存在）

若存在 `coverage/{SYMBOL}/current.md`：
- 解析指针
- 读取当前 thesis
- 提取 Invalidation Conditions 与头寸管理原则

若不存在：
- 进入 news-only 模式
- 明确提示建议先 initiate coverage

### 3. 识别市场并获取最新数据

- A 股：优先 `cn_market_data_tools.py`
- 美股/其他：获取当前价格、近期新闻、必要的市场上下文

### 4. 按三维度分析

结构上遵循 `app/prompts/asset_analysis.md`：
- Fundamental
- Valuation
- Technical

若 thesis 存在，应按“thesis 原判断 → 新变化 → 当前结论”来写。

### 5. Invalidation Check

若 thesis 存在，对每条 IC 判断：
- TRIGGERED
- WATCHING
- CLEAR
- UNVERIFIABLE

### 6. 给出 Suggested Action

只选一个主动作：
- Hold
- Monitor
- Trim
- Exit
- Update thesis
- Initiate coverage

## Notes

- 成本价不是建议依据
- 对 valuation 的 forward 数据要继续遵守年份错位校验要求
- 若三维度冲突，要直接说明哪个维度优先以及为什么
