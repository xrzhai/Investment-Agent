# Investment-Agent Project Context

## 项目目标

帮助长期投资者维护一个可回看、可解释、可复盘的投资组合工作流：
- 持仓状态是确定性的
- thesis 是结构化、版本化的
- 决策与复盘有归档
- agent 用来协助研究、检查与总结，而不是替代执行
- agent 自己的操作错误也应被记录并召回，避免重复犯错

## 核心数据层

- DB：`data/investment.db`
- Coverage 指针：`coverage/{SYMBOL}/current.md`
- Coverage 模板：`coverage/THESIS_TEMPLATE.md`
- Review 归档：`reviews/`
- 投资原则：`config/principles.md`
- 投资者配置：`config/profile.json`

## 推荐接口分层

1. Core logic
   - `app/engines/`
   - `app/services/`
   - `app/repositories/`
   - `app/models/`
2. Tool layer
   - `app/tools/*.py`
   - 这是 agent 的主接口层
3. Thin CLI
   - `python run.py ...`
   - 只用于人工原子操作与调试
4. Workflow docs
   - `skills/investment-agent/workflows/*.md`

## 核心约束

- `avg_cost` 不传入任何建议逻辑；它只用于 P&L 展示
- 所有数值计算（PnL / 权重 / CAGR / policy checks）必须由 Python 完成
- Invalidation Conditions 是首要约束；触发时优先级高于叙事和情绪
- 无 coverage thesis 的标的，不应直接给出 thesis-driven 的加仓建议
- postmortem 记录的是 agent 的操作错误，不是投资观点本身

## 数据质量坑

### 1. yfinance `eps_forward` 年份错位

已知问题：`eps_forward` 往往返回 FY+2E，而不是 FY+1E。

影响：
- 会让 Forward P/E 被低估约 10–25%
- 如果直接写入 thesis，会扭曲 valuation 判断

要求：
- 写入 thesis 前，必须通过 StockAnalysis 或第二数据源交叉验证
- 所有 EPS / P-E 数字要标注来源与财年

### 2. ADR 估值比率不可直接用

如 TSM 等 ADR：
- `ps_ratio`
- `ev_ebitda`

可能因为货币混用而失真，应手算或省略。

### 3. A 股基本面走 JQData

A 股标的（`.SH` / `.SZ` / `.BJ`）的基本面数据优先使用：
- `app/tools/cn_market_data_tools.py`
- 底层依赖 `.env` 中的 `JQ_USER` / `JQ_PASS`

不要把 yfinance 当作 A 股基本面主数据源。

## Coverage 文件约定

每个标的一个目录：

```text
coverage/{SYMBOL}/
├── v1_YYYY-MM-DD.md
├── v2_YYYY-MM-DD.md
└── current.md
```

`current.md` 只存一行：当前生效版本的文件名。

Thesis 至少包含：
- Fundamental
- Valuation
- Technical
- Invalidation Conditions
- 头寸管理原则
- 覆盖历史

## reviews/ 约定

- `reviews/daily/`：日检输出
- `reviews/suggest/`：组合建议输出
- `reviews/decisions/`：调仓决策与执行记录
- `reviews/REVIEWS_LOG.md`：统一索引

## Postmortem / mistake memory

使用工具：
- `app/tools/postmortem_tools.py`

用途：
- 记录 agent 的数据误读、逻辑错误、漏步骤、格式错误
- 在后续任务前召回相关教训，做自查

不应用于：
- 记录普通投资结论
- 替代 coverage thesis 或 review archive


## LLM integration layer

当前项目通过 `app/services/llm_client.py` 调用一个可配置的 LLM CLI。

默认配置：
- `INVESTMENT_AGENT_LLM_CMD=claude`
- `INVESTMENT_AGENT_LLM_ARGS="--print --tools '' --no-session-persistence"`

这意味着：
- 当前默认体验仍然是 Claude CLI
- 但架构上不再依赖某个特定 Python SDK
- 若切换到其他命令，需要保证它支持兼容的非交互参数模式

## 什么时候优先用 tools，而不是 CLI

优先用 tools：
- agent 需要结构化输出
- 需要 workflow 内串联多个原子步骤
- 需要 JSON 结果供后续判断

优先用 CLI：
- 人工快速导入 / 查看 / refresh / check
- 本地 smoke test
- 最简单的手动操作
