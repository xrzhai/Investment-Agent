# 投资研究 Harness — Agent 指南

## 1. 这个仓库是什么

这是一个供外部 Agent 使用的个人投研知识库与组合管理工具箱，承担三个职能：

1. **记录与回顾**：保存公司研究、专题思考、决策和组合事件；
2. **研究与想法生成**：从历史记录和新证据中继续推理、发现联系并形成新 idea；
3. **投资组合管理**：维护持仓、现金、出入金、交易、期权和组合复盘所需的结构事实。

Harness 的作用是把用户的思想、资料入口和少量可靠工具交给 Agent。它不是研究规则引擎，也不替 Agent 决定能读什么、读多少或采用什么写法。

内容分三个区：`research/`（公司研究、专题、宏观、研究思想）、`portfolio/`（原则、记录、账本）、`playbook/`（工作提示、模板、约定）。工程目录 `harness/`、`scripts/`、`tests/` 在根目录。

## 2. 核心原则

- **上下文用于扩展思考，不用于限制思考。** 可以从摘要或索引开始，也可以在问题展开后自由阅读完整 thesis、历史笔记、其他公司案例、review 和原始来源。
- **Workflow 是可选提示。** `playbook/workflows/` 提供常见任务的思考起点，可以组合、跳过或改写；不需要把任务强行归入唯一类型。
- **没有研究上下文预算。** 不按字符数、fact 数量或文件数量裁剪研究材料。上下文较大时由 Agent 搜索、分批阅读和自行总结，并在需要时回到原文。
- **Markdown 是主要知识载体。** Tags、indexes 和 front matter 只帮助检索与延续，不要求所有思考结构化。
- **同一事实只手工维护一处。** 能链接就不复制；会随版本过期的信息（版本号、截至日、估值状态）只写在正文里。
- **研究作品应有主见。** 围绕真正决定价值的问题组织材料，允许追随意外证据、提出新框架并保留不确定性。
- **确定性代码只处理适合代码的问题。** 组合事务、报价、现金流和快照使用结构化工具；研究推理不由程序裁剪或评分。

## 3. 建议的起点

进入仓库先读本文件。之后按问题选择上下文，而不是执行固定读取顺序：

- 公司研究通常值得读 `research/context.md`；
- `research/INDEX.md` 汇总公司 coverage、专题、宏观和缺档线索；
- 单个公司从 `research/coverage/{SYMBOL}/` 的摘要（summary 或 README）和 `current.md` 开始；
- 宏观定期观察可从 `research/macro/current.md` 和 `playbook/workflows/macro-observation.md` 开始；
- 组合复盘和仓位决策可以再读 `portfolio/principles.md` 与 `portfolio/LOG.md`；
- 当前 thesis、公司内 `research_notes/` 与 `archive/`、`research/topics/`、`portfolio/` 下的记录和 `source_docs/` 都可以在相关时阅读；
- 使用 `rg`、文件名和链接寻找上下文，避免无目的地把整个仓库一次性展开。

摘要和索引只是地图。不能用摘要代替本来需要完整阅读的 thesis，也不能因为某份材料不在默认路线中就忽略它。

## 4. Research 与 Portfolio

估值属于 Research。公开价格、市值、enterprise value、consensus、情景假设、隐含预期和 owner earnings 都可以进入公司研究。

个人数量、成本、盈亏、当前/目标权重和交易规模属于 Portfolio。做纯公司研究时，通常先独立形成商业与估值判断，再按需要引入组合语境；这是为了减少锚定，不是程序禁读规则。真正的仓位决策可以同时使用两个事实域，并把两种理由说清楚。

组合数据库通过 `harness.portfolio` 的确定性函数维护，不使用临时 SQL 修改。没有用户明确确认和外部执行证据，不能下单，也不能暗示交易已经执行。

## 5. 事实、来源与历史观点

- 重要的当前事实尽量保留来源、日期/期间和可核验定位；
- 区分公司报告、管理层 guidance、市场 consensus、分析假设和推断；
- 旧 thesis、研究笔记和 prior Agent output 是理解历史思想的上下文，不自动成为当前事实；
- 证据冲突或缺失时直接说明，不用记忆填补；
- 部分公司保留的 `facts.jsonl`、`sources.json` 是冻结的历史记录，可直接阅读，格式见 `playbook/contracts/research-facts.md`；新研究不要求补充结构化记录，来源直接写在正文或 `source_docs/` 中即可。

## 6. 写入与记录

新产物的位置：

| 产物 | 位置 |
|---|---|
| 公司 thesis 新版本 | `research/coverage/{SYMBOL}/vN_YYYY-MM-DD.md`，并改写 `current.md` |
| 被替代的旧版本 | 该公司 `archive/versions/`；已完成的单次报告放 `archive/notes/` |
| 公司专属补充分析、跟踪笔记 | 该公司 `research_notes/`；持续验证点写 `tracking.md` |
| 跨公司想法、框架、类比 | `research/topics/`，并在 `research/INDEX.md` 专题表补一行 |
| 宏观观察 | `research/macro/`，并更新其 `current.md` |
| 组合复盘、对账 | `portfolio/reviews/YYYY/` |
| 决策 / 成交说明 | `portfolio/decisions/` / `portfolio/executions/` |
| 重要组合或研究活动 | 在 `portfolio/LOG.md` 追加一行 |

- `current.md` 是唯一的版本指针：索引和摘要不另记"当前版本"，摘要只注明"本摘要基于"哪一版；升版后若摘要内容也变了，一并更新摘要；
- 新增公司 coverage 时在 `research/INDEX.md` 补一行；升版时索引不需要改动；
- 组合报价只用 `scripts/refresh_quotes.py` 刷新，估值完整且拉取无报错时会自动记录当日快照；
- Raw source 不静默覆盖；修正时保留原因和新来源；
- `summary.md` 用于导航，可以短，但不限制完整 thesis 的形状或长度；
- 组合成交、现金流和期权状态变化使用结构化事务记录；
- Validation 和 tests 是诊断工具，只在相称时运行，不能作为研究内容的发布门禁。

## 7. 默认写作语言

面向用户的回答，以及新生成或更新的研究、摘要、状态说明、事实、来源说明、复盘和组合报告，默认使用简体中文。Ticker、ID、字段名、文件名、原始指标和必要专业术语可以保留英文。只有用户明确要求时才切换主要语言。
