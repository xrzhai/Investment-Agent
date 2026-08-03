# Investment Research Harness

这是一个供 AI Agent 进入后使用的个人投研管理仓库。

它不是内置 Agent 的应用，不提供自动交易，也不把 LLM 调用封装进项目。Agent 负责研究、判断和编排；仓库负责流程、事实、确定性计算、校验与归档。

## 核心定位

- **Research-first**：主要服务公司基本面研究、财报更新、thesis 维护和长期跟踪。
- **Portfolio-aware**：保留持仓、现金、期权、交易、快照和组合规则，但研究任务默认不加载这些信息。
- **Context-safe**：按任务选择最小上下文，历史版本、原始材料和交易信息不会自动进入研究上下文。
- **Source-grounded**：结构化事实必须带来源、时点和适用期间；研究笔记不能自动升级成事实。
- **Human-controlled**：Agent 可以辅助研究、记录和检查，但不能自动下单或替用户做最终承诺。

## Agent 从哪里开始

进入仓库后先读 [AGENTS.md](AGENTS.md)。它定义：

1. 不同任务应读取哪些文件；
2. 哪些目录默认禁止递归加载；
3. Research 与 Portfolio 什么时候可以合并；
4. 如何更新 thesis、事实、来源和组合状态；
5. 写入后的校验要求。

## 目录

```text
AGENTS.md          Agent 入口与执行边界
contracts/         架构、上下文、事实和组合数据契约
workflows/         按任务路由的工作流
templates/         research / review / decision 模板
harness/           确定性 Python 能力，无内置 Agent、无产品 CLI
coverage/          每个标的的研究工作区
reviews/           组合复盘、决策与执行记录
config/            投资原则和组合约束
data/              本地 SQLite 结构化组合事实源
research_notes/    历史/专题研究；默认不进入任何上下文
tests/             Harness 契约与污染防护测试
```

## 两个事实域

### Research domain

文件是主要事实载体：

- `coverage/{SYMBOL}/current.md`：当前 thesis 指针；
- `coverage/{SYMBOL}/status.json`：最小研究状态；
- `coverage/{SYMBOL}/facts.jsonl`：来源化结构事实；
- `coverage/{SYMBOL}/sources.json`：来源登记；
- `coverage/{SYMBOL}/summary.md`：供跨标的/组合任务读取的短摘要；
- thesis、估值底稿和原始材料：仅在具体任务需要时读取。

现有 coverage 可以继续使用旧结构；Harness 会以 legacy-compatible 方式读取，并逐个标的迁移。

### Portfolio domain

SQLite 继续保存适合事务和查询的结构事实：

- 持仓与现金；
- 低频交易和现金流；
- 期权合约；
- 报价及其来源；
- 组合快照；
- 追加式 portfolio events。

Agent 不直接修改数据库，而是调用 `harness.portfolio` 中的确定性函数。研究任务默认不读取数据库。

数据库只记录低频、紧凑的结构事件，不保存 PDF、thesis 正文或对话。正常使用一年通常只增长几 MB；更重要的是 Agent 永远读取有上限的查询结果，而不是读取整个数据库。详见 `contracts/retention.md`。

外部 Agent 的最小 Python 入口是 `InvestmentHarness`：

```python
from harness import ContextRequest, ContextTask, InvestmentHarness

harness = InvestmentHarness()
pack = harness.context(ContextRequest(task=ContextTask.research_scan, symbol="NVDA"))
```

正常成交通过 `PortfolioStore.record_trade()` 记录，并同时传入决策记录的
`decision_ref` 与券商/执行证据的稳定 `execution_ref`。Harness 不提供下单能力。

## 不再包含

- Typer / Rich 人工 CLI；
- 内置 Claude、OpenAI 或其他 LLM client；
- recommendation engine；
- Agent 编排循环；
- 自动下单；
- 把旧 thesis、source docs 或所有 review 一次性塞进上下文的工作流。

## 开发验证

项目使用 `pyproject.toml` 声明依赖。验证 Harness：

```text
python -m pytest
```

这只是开发/校验入口，不是面向用户的投资 CLI。

## 隐私

真实数据库、coverage 正文、来源文件和 reviews 默认保留在本地并由 `.gitignore` 排除。公开仓库只保留 Harness、契约、模板和空目录骨架。

## License

- 代码：PolyForm Noncommercial 1.0.0
- 文档、workflow、模板：CC BY-NC 4.0
