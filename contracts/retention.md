# 组合数据保留说明

## 原则

Research 正文、来源文档和 Agent 对话继续保存在文件中。SQLite 只保存适合事务和查询的
组合事实，不保存大块 Markdown、PDF 或 prompt。

## 长期保留

- portfolio events、cashflow events 和期权状态变化；
- 当前持仓读取模型；
- 实际被 review、decision 或 execution 使用的报价；
- 有意义的组合 snapshots；
- 与事件相关的稳定 references。

这些数据增长很慢，不需要为了节省空间删除审计历史。

## Agent 如何读取

Agent 可以根据问题查询当前状态或历史窗口，并在需要时继续向前追溯。接口可以分页，
但仓库不设置全局上下文预算，也不规定一次研究最多查看多少事件。

通常没有必要把整个 SQLite dump 放进对话；应优先查询需要的行和时间范围。若研究发现
更早历史相关，可以继续扩展查询。

## 维护

- 数据库 schema 迁移前先备份；
- 定期维护时可以运行 `PRAGMA integrity_check`；
- 保留 events 和 cashflows；
- 只有实际数据规模证明有必要时，才引入归档或分库。
