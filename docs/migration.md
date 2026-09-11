# 迁移说明

## 已完成的方向变化

仓库已经从“内置 LLM 的 CLI 应用”转为“外部 Agent 可直接阅读的投研知识库，外加
少量确定性组合工具”。

已移除或不再需要的应用概念包括：产品化 CLI、内置 model client、recommendation
engine、Agent 编排循环以及自动交易。

## 现有 SQLite 数据库

`data/investment.db` 继续作为私有组合数据库。迁移真实数据库前应先备份，并使用
`PortfolioStore` 的幂等方法建立 events、quotes 和 instrument metadata。仅仅 import
`harness` 不会修改数据库。

有价值的 legacy rows 可以按需导出为 Markdown，保留 row ID 和历史时点。Prior Agent
output 是历史语境，不自动成为当前建议，也不回放成新的 portfolio event。

## 现有 Research

Legacy `coverage/{SYMBOL}` 可以继续通过 `current.md` 或原有 README 工作。进入主动研究
时，Agent 直接阅读原文，并根据实际需要决定是否补充 `status.json`、`summary.md`、
`facts.jsonl` 或 `sources.json`。

迁移不要求：

- 把每篇旧 thesis 或笔记拆成 atomic facts；
- 把长文压缩成固定长度摘要；
- 删除研究与组合语境混合的历史原文；
- 让所有公司使用同一套章节或 checklist。

新 thesis 可以重新组织旧判断、刷新事实和估值，并说明为什么改变。摘要、索引和 tags
用于导航；Agent 随时可以继续阅读完整历史材料和来源。

仓库不再提供 Context Router 或 legacy thesis 截断视图。需要区分 Research 与 Portfolio
时，由 Agent 理解完整原文，并在当前产物中按任务重新组织。
