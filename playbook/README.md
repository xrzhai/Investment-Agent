# Playbook：工作提示、模板与约定

这里放 Agent 研究、记录和维护时可以参考的材料。它不是路由表：Agent 不需要先给任务分类，
也不需要选择唯一 workflow，可以组合、跳过或改写这些提示。

## workflows/ — 可选工作提示

- [`research.md`](workflows/research.md)：公司研究、事件跟踪、历史泛化和估值时可参考的问题；
- [`macro-observation.md`](workflows/macro-observation.md)：中美宏观月度观察、半年复核及数据口径；
- [`portfolio-review.md`](workflows/portfolio-review.md)：查看整体组合时可参考的维度（含报价刷新入口）；
- [`decision.md`](workflows/decision.md)：需要形成明确仓位动作时的记录提示；
- [`trade-record.md`](workflows/trade-record.md)：记录外部已执行交易时的事务要求；
- [`postmortem.md`](workflows/postmortem.md)：值得留下流程经验时的复盘提示。

## templates/ — 可选写作起点

`research/`（thesis、摘要、idea note，以及冻结 facts/sources 的格式样例）、`portfolio/`（决策、复盘）
和 `postmortem.md`。模板只是空白起点，不是强制大纲。

## contracts/ — 约定

- [`architecture.md`](contracts/architecture.md)：仓库架构、两种数据形态、上下文使用与明确不做的事；
- [`portfolio-state.md`](contracts/portfolio-state.md)：组合事件、报价、现金流规则，以及数据保留与维护；
- [`research-facts.md`](contracts/research-facts.md)：冻结的 `facts.jsonl` / `sources.json` 格式说明。

## history/ — 已完成的变更记录

- [`migration-2026-08.md`](history/migration-2026-08.md)：从内置 LLM 的 CLI 应用转为外部 Agent 知识库；
- [`2026-10-reorganization.md`](history/2026-10-reorganization.md)：2026-10-09 目录整理与旧路径对照。

Research 的范围、阅读路径和写作结构由问题本身决定。唯一不能自由推断的是交易执行：
没有用户确认和外部 evidence，不能记录为已成交。
