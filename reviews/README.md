# 复盘、决策与执行记录

本目录保存可供人和 Agent 阅读的组合历史语境，包括 portfolio review、decision、
execution 和 postmortem。

推荐但不强制的目录：

```text
reviews/
  REVIEWS_LOG.md
  portfolio/YYYY/YYYY-MM-DD.md
  decisions/YYYY/YYYY-MM-DD_SYMBOL.md
  executions/YYYY/YYYY-MM-DD_SYMBOL.md
  postmortems/YYYY/YYYY-MM-DD_slug.md
```

Agent 可以在研究需要理解决策演化、行为偏差、组合约束或历史假设时阅读这些记录。
历史仓位和 prior recommendation 不是当前公司事实，使用时应注明时间和角色。

真正的成交记录仍需引用用户批准的 decision 和外部 execution evidence。历史 Markdown
不回放成新的组合事件；当前组合事实以 SQLite 为准。

真实 review 默认保留在本地并由 `.gitignore` 排除。
