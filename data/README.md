# 私有组合数据

`investment.db` 是本地 SQLite 事实源，用于保存持仓、现金、期权、报价、快照和组合事件。数据库文件默认由 `.gitignore` 排除。

不要把整个数据库作为 Agent 上下文读取，也不要使用临时 SQL 直接修改。请通过 `harness.portfolio.PortfolioStore` 操作；数据库结构迁移前先备份，并使用 `contracts/retention.md` 中定义的有界状态与事件查询。
