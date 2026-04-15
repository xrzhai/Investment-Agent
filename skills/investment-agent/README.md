# Investment-Agent Workflow Skills

这不是某个单一 agent 的配置目录，而是这个项目的通用 workflow 文档层。

目标：
- 让人和 AI agent 都能看懂项目怎么用
- 把高阶流程从 `.claude/commands/` 抽离出来
- 让 agent 主要基于 `app/tools/*.py` 和 repo 内文件工作，而不是依赖某个专用 slash command 系统

## 建议使用顺序

1. 先读 `project-context.md`
   - 理解数据源、核心约束、目录结构、数据质量坑
2. 再读对应 workflow
   - `workflows/daily-review.md`
   - `workflows/researcher-initiate.md`
   - `workflows/researcher-update.md`
   - `workflows/risk-ic.md`
   - `workflows/trader-decide.md`
   - `workflows/trader-record.md`
3. 执行时优先调用：
   - `app/tools/*.py`
   - 必要时再使用薄 CLI `python run.py ...`

## 设计原则

- Agent-neutral first：不假设 Claude / Hermes / Codex 专属能力
- Tool-first：缺原子能力时优先补 tool，不优先补大而全 CLI 命令
- Deterministic before generative：算术、状态、规则由 Python 完成；语言解释才交给 LLM
- Archive everything important：review / decision / thesis 更新要留痕

## 当前范围

第一批迁移的 workflow：
- Daily review
- Researcher initiate / update
- Risk IC sweep
- Trader decide / record

后续可继续补：
- PM suggest
- Researcher analyze / note / status
- Postmortem workflows
