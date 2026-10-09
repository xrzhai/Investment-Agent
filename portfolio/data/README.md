# 私有组合数据

`investment.db` 是本地 SQLite 事实源，用于保存持仓、现金、期权、报价、快照和组合事件。本目录除本说明外默认由 `.gitignore` 排除。

不要把整个数据库作为 Agent 上下文读取，也不要使用临时 SQL 直接修改。请通过 `harness.portfolio.PortfolioStore` 操作；数据库结构迁移前先备份，并使用 `playbook/contracts/portfolio-state.md` 中"数据保留与维护"一节定义的有界状态与事件查询。只读诊断应以 SQLite `mode=ro` 连接，部分读取方法会调用 `ensure_schema()`。

```text
portfolio/data/
  investment.db            当前账本
  backups/                 历史数据库备份（结构迁移或大额事务前留存）
  artifacts/               账本相关附件：持仓权重图、券商报告渲染页等
  LEDGER_CUTOVER.md        账本切换基线与不得重复记账的原因
  legacy_data_lessons.md   旧数据错误提醒
```
