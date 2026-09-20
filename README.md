# 投资研究 Harness

这是一个供 AI Agent 使用的个人投研知识库与组合管理仓库。

它不内置 LLM，不提供自动交易，也不试图把研究变成一条固定流水线。Agent 负责
阅读、研究、判断和创作；仓库负责保存用户的投资思想、历史语境、研究材料以及少量
确实需要确定性的组合工具。

## 三个职能

| 职能 | 主要内容 | 入口 |
|---|---|---|
| 记录与回顾 | 公司研究、专题笔记、决策理由、组合事件和复盘 | `coverage/`、`research_notes/`、`reviews/` |
| Research / idea generation | 从已有记录和新证据继续推理，形成新问题、观点或 thesis | `config/research-context.md`、`workflows/`、知识索引 |
| 投资组合管理 | 持仓、现金、出入金、交易、期权、报价和组合快照 | `harness/portfolio/`、`data/investment.db` |

## 设计原则

- Harness 提供上下文，不限制上下文；
- Workflow 是可选的研究提示，不是任务门禁；
- Agent 可以自由阅读完整 thesis、历史笔记、来源和跨公司案例；
- Markdown 是主要知识载体，结构化只用于确有复用或事务价值的内容；
- 估值属于公司研究，个人成本、盈亏和仓位属于组合管理；
- 研究可以自由组织，但重要事实应尽量保留来源和时点；
- 任何交易都需要用户确认和外部执行证据。

## Agent 从哪里开始

先读 [AGENTS.md](AGENTS.md)。公司研究通常再读
[`config/research-context.md`](config/research-context.md)。之后可以使用摘要、索引、
tags 或 `rg` 找到相关资料，并随着问题展开自由扩展阅读范围。

`status.json`、`summary.md` 和知识索引只是导航。仓库没有字符预算、fact 数量预算，
也不会把完整 thesis 裁成固定大小的 context pack。

## 目录

```text
AGENTS.md          Agent 指南与基本边界
config/            用户的研究思想、投资原则和组合偏好
coverage/          公司研究、thesis、来源与历史版本
research_notes/    探索性笔记、专题研究和 idea
reviews/           组合复盘、决策、执行记录和过程复盘
workflows/         可选的研究/记录提示卡
templates/         可选写作起点
contracts/         来源、组合事务和存储约定
harness/research/  可选的来源/事实/版本辅助工具
harness/portfolio/ 确定性的组合事务与计算
data/              私有 SQLite 组合事实
tests/             确定性代码的测试
```

## Research

LLM 可以直接理解 Markdown。旧 thesis、笔记和 review 不需要全部转成 JSON；只有需要
跨任务复用、筛选、来源追踪或当前状态管理的内容，才值得补充 `facts.jsonl`、
`sources.json`、tags 或索引。

正式公司覆盖通常保留 `current.md` 指针和版本化 thesis。估值应注明观察日期和关键
假设，但写法、章节和研究路径由 Agent 根据公司决定。

## Portfolio

SQLite 保存适合事务处理的结构事实，例如持仓、现金、期权、报价和事件。Agent 通过
`harness.portfolio` 修改这些数据，避免重复记账和部分写入。研究正文和原始来源不放进
数据库。

Python 是可选工具，不是研究入口。没有门面 API 类，按需直接用薄函数：

```python
# 组合侧（确定性写/算）：薄函数直调
from harness.portfolio import PortfolioService, PortfolioStore
from harness.settings import HarnessPaths

paths = HarnessPaths.discover()
store = PortfolioStore(paths=paths)
service = PortfolioService(store, paths=paths)
state = service.get_state()        # 组合估值
report = service.refresh_quotes()  # 拉价 + 落库（日常直接跑 scripts/refresh_quotes.py）
```

研究侧不需要 Python：直接读 `coverage/{SYMBOL}/` 下的 Markdown 与 JSONL，或搜索
`research_notes/`、`reviews/` 中的材料。

## 隐私

真实数据库与组合记录（`data/`、`reviews/**`、含成本价的组合文件）只存在于本地，
由 `.gitignore` 排除；组合事实的权威来源是本地 `data/investment.db`。公开仓库只
包含可分享的指南、工具和空目录骨架，以及公司 coverage 等
公开市场研究正文。

## 许可证

- 代码：PolyForm Noncommercial 1.0.0；
- 文档、workflow 和 template：CC BY-NC 4.0。

详见 [LICENSES.md](LICENSES.md)。
