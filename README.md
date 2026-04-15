# Investment Agent

一个面向长期投资者的 thesis-driven portfolio workflow 项目。

它不是券商，不是自动交易系统，也不是 Agent 框架。它做的事情很简单：
- 用 Python 维护确定性的持仓、现金、PnL、权重与规则检查
- 用 coverage thesis 文件维护每个标的的投资论点与失效条件
- 用 reviews/ 归档日检、建议与决策记录
- 用 postmortem 记录 agent 自己的操作错误，避免重复犯错
- 让任意 AI agent 基于 workflow docs + tools 协助你完成研究与复盘

## 项目定位

这是一个 tool-first、workflow-driven 的小项目：
- `app/tools/*.py` 是 agent 最适合调用的原子工具接口
- `skills/investment-agent/` 是主要工作流文档
- `python run.py ...` 是一个薄 CLI，方便人工录入、查看和调试

非目标：
- 不自动下单
- 不提供前端 UI
- 不封装成通用 Agent framework

---

## 核心组成

1. Deterministic portfolio state
   - 持仓、现金、价格、PnL、权重、policy checks 都由 Python 计算
2. Coverage thesis system
   - 每个标的一份版本化 thesis，包含 Fundamental / Valuation / Technical、Invalidation Conditions、头寸管理原则
3. Review archive
   - `reviews/` 下保留 daily / suggest / decision 等记录，便于回看与复盘
4. Mistake memory
   - 用 `postmortem_tools.py` 记录 agent 的操作错误、根因和预防规则
5. Tool scripts
   - agent 可直接调用的工具脚本，优先输出结构化结果
6. Thin CLI
   - 适合人工做原子操作：导入、刷新、查看、检查

---

## 两种使用方式

### 1) Manual mode：直接用薄 CLI

适合：
- 初始化项目
- 手动录入持仓
- 快速查看 summary / refresh / check
- 做本地 smoke test

常用命令：

```bash
python run.py portfolio import portfolio.csv
python run.py portfolio summary
python run.py portfolio refresh
python run.py portfolio check
python run.py analyze portfolio
python run.py analyze asset NVDA
```

### 2) Agent-assisted mode：workflow docs + tools

适合：
- daily review
- portfolio suggest
- coverage initiate / update
- researcher analyze / note / status
- risk IC sweep
- trader decision / record
- postmortem create / list / self-check

入口文档：
- `skills/investment-agent/README.md`
- `skills/investment-agent/project-context.md`
- `skills/investment-agent/workflows/*.md`

执行时优先调用：
- `app/tools/*.py`
- 必要时再使用薄 CLI `python run.py ...`

---

## 快速开始

### 环境准备

```bash
pip install -r requirements.txt
cp .env.example .env
```

如果使用 A 股数据，需要在 `.env` 中配置：
- `JQ_USER`
- `JQ_PASS`

### 初始化与查看

```bash
# 导入持仓（CSV: symbol,quantity,avg_cost[,market]）
python run.py portfolio import portfolio.csv

# 查看持仓
python run.py portfolio summary

# 拉取最新价格
python run.py portfolio refresh

# 跑规则检查
python run.py portfolio check
```

---

## 关键目录

```text
investment-agent/
├── run.py
├── app/
│   ├── cli/            # 薄 CLI，面向人工原子操作
│   ├── engines/        # 业务逻辑（确定性计算）
│   ├── services/       # 市场数据、LLM、coverage 等服务
│   ├── repositories/   # SQLite CRUD
│   ├── models/         # Domain models / DB models
│   ├── prompts/        # Prompt 模板
│   └── tools/          # Agent 可直接调用的工具脚本
├── skills/
│   └── investment-agent/
│       ├── README.md
│       ├── project-context.md
│       └── workflows/
├── coverage/           # 标的 thesis 与 current.md 指针
├── reviews/            # daily / suggest / decision 归档
├── config/             # 投资原则、投资者配置
└── data/               # SQLite DB（运行时生成）
```

---

## Architecture summary

Current structure in one line:
- code and workflow live in Git
- real portfolio state stays local
- `skills/investment-agent/` is the main workflow layer
- `app/tools/*.py` is the main automation surface
- `python run.py ...` stays as a thin manual CLI

If you want to understand how the project works, read in this order:
1. `README.md`
2. `skills/investment-agent/README.md`
3. `skills/investment-agent/project-context.md`
4. the workflow docs under `skills/investment-agent/workflows/`

---

## Privacy / local data

This repository is designed to keep the code and workflow public while leaving real portfolio data local.

By default, the following should remain local-only:
- `data/` runtime database
- `reviews/` daily / suggest / decision history
- most real `coverage/{SYMBOL}/` thesis files
- local benchmark or evaluation outputs

The repository keeps workflow docs and templates, but your live portfolio state and research history should stay on your machine.

---

## 当前 LLM CLI 配置

当前默认配置是：
- command: `claude`
- args: `--print --tools '' --no-session-persistence`

可以通过环境变量覆盖：

```bash
export INVESTMENT_AGENT_LLM_CMD=claude
export INVESTMENT_AGENT_LLM_ARGS="--print --tools '' --no-session-persistence"
```

注意：当前包装器本质上是 CLI-driven 的，要求目标命令支持兼容的非交互调用模式。

---

## 数据与分析原则

- 确定性优先：PnL / 权重 / policy checks / CAGR 由 Python 计算，不让 LLM 做算术
- 成本价不入决策：`avg_cost` 只用于展示，不进入建议逻辑
- Thesis 优先：Invalidation Conditions 是首要约束，触发时不能找借口
- 数据质量优先：yfinance 的 `eps_forward` 存在年份错位，写入 thesis 前必须交叉验证
- Agent 只做解释与流程协助，不做自动执行

更多约束见：
- `skills/investment-agent/project-context.md`
- `coverage/THESIS_TEMPLATE.md`

---

## 当前状态

这个项目已经可以作为一个开源的个人投资工作流项目使用，但仍在持续整理：
- workflow docs 已独立于 agent-specific command 系统
- CLI 已收缩为更薄的人工入口
- `.claude/` 适配层已删除
- 剩余历史性文档和归档记录会继续逐步清理，但不影响当前主结构
- LLM 集成保持为可配置 CLI 包装器，而不是绑定某个 Python SDK
