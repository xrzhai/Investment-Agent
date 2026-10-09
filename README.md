# 投资研究 Harness

这是一个供 AI Agent 使用的个人投研知识库与组合管理仓库。

它不内置 LLM，不提供自动交易，也不试图把研究变成一条固定流水线。Agent 负责
阅读、研究、判断和创作；仓库负责保存用户的投资思想、历史语境、研究材料以及少量
确实需要确定性的组合工具。

## 三个内容区

| 区域 | 回答的问题 | 入口 |
|---|---|---|
| [`research/`](research/README.md) | 这家公司或机制如何运作，价值如何形成，当前证据支持什么判断？ | `research/INDEX.md`、`research/context.md` |
| [`portfolio/`](portfolio/README.md) | 组合现在是什么状态，为什么行动，结果与约束是什么？ | `portfolio/LOG.md`、`portfolio/principles.md`、`portfolio/data/investment.db` |
| [`playbook/`](playbook/README.md) | Agent 如何研究、记录、核验和维护这些内容？ | 工作提示、写作模板、数据约定 |

工程目录按惯例留在根目录：`harness/`（Python 包）、`scripts/`（日常脚本）、`tests/`。

## 设计原则

- Harness 提供上下文，不限制上下文；
- Workflow 是可选的研究提示，不是任务门禁；
- Agent 可以自由阅读完整 thesis、历史笔记、来源和跨公司案例；
- Markdown 是主要知识载体，结构化只用于确有复用或事务价值的内容；
- 同一事实只手工维护一处：公司当前正文只由 `current.md` 指出；
- 估值属于公司研究，个人成本、盈亏和仓位属于组合管理；
- 研究可以自由组织，但重要事实应尽量保留来源和时点；
- 任何交易都需要用户确认和外部执行证据。

## Agent 从哪里开始

先读 [AGENTS.md](AGENTS.md)。公司研究通常再读 [`research/context.md`](research/context.md)，
然后从 `research/INDEX.md`、公司摘要、tags 或 `rg` 找到相关资料，并随着问题展开自由
扩展阅读范围。摘要和索引只是导航；仓库没有字符预算，也不会把完整 thesis 裁成固定
大小的 context pack。

## 目录

```text
AGENTS.md             Agent 指南与基本边界
research/
  INDEX.md            研究导航（公司、专题、宏观、缺档线索）
  context.md          用户的研究思想
  coverage/{SYMBOL}/  公司研究：current.md 指针、正文、摘要、跟踪、来源、归档
  topics/             跨公司专题与探索性笔记
  macro/              中美宏观月度观察与半年复核
portfolio/
  LOG.md              组合活动时间线
  principles.md       投资原则与风险边界
  profile.json        结构化组合偏好
  reviews/ decisions/ executions/   复盘、决策、成交记录
  data/               SQLite 账本、历史备份、账本边界说明与附件
  archive/            已退出工具的历史输出
playbook/
  workflows/          可选的研究/记录提示卡
  templates/          可选写作起点
  contracts/          架构、组合事务与研究记录约定
  history/            已完成的迁移与整理记录
harness/portfolio/    确定性的组合事务与计算
scripts/              报价刷新（含当日快照）与 TWR 报告
tests/                确定性代码的测试
```

## Research

LLM 可以直接理解 Markdown。旧 thesis、笔记和 review 不需要转成 JSON。公司覆盖保留
`current.md` 指针和版本化 thesis；被替代的版本移入该公司的 `archive/`。估值应注明
观察日期和关键假设，但写法、章节和研究路径由 Agent 根据公司决定。

部分公司保留的 `facts.jsonl`、`sources.json` 是冻结的历史记录，可以直接阅读；新研究
不要求补充结构化记录。研究侧不需要 Python。

宏观观察入口：[中美宏观观察](research/macro/README.md)与
[最新一期](research/macro/current.md)（本地研究记录）。按月观察，半年复核分布、保障和债务。

## Portfolio

SQLite 保存适合事务处理的结构事实，例如持仓、现金、期权、报价和事件。Agent 通过
`harness.portfolio` 修改这些数据，避免重复记账和部分写入。研究正文和原始来源不放进
数据库。

```bash
python scripts/refresh_quotes.py              # 拉价 + 落库；估值完整时自动记录当日快照
python scripts/twr_report.py                  # 时间加权收益摘要
```

```python
from harness.portfolio import PortfolioService, PortfolioStore
from harness.settings import HarnessPaths

paths = HarnessPaths.discover()
store = PortfolioStore(paths=paths)
service = PortfolioService(store, paths=paths)
state = service.get_state()        # 组合估值
```

## 隐私

真实研究正文、组合记录与数据库（`research/` 与 `portfolio/` 下除公开说明以外的内容）
只存在于本地，由 `.gitignore` 排除；组合事实的权威来源是本地
`portfolio/data/investment.db`。公开仓库只包含可分享的指南、工具、研究思想、组合原则
与空目录骨架。

## 许可证

- 代码：PolyForm Noncommercial 1.0.0；
- 文档、workflow 和 template：CC BY-NC 4.0。

详见 [LICENSES.md](LICENSES.md)。
