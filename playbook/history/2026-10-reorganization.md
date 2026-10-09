# 2026-10-09 目录整理

## 为什么整理

整理前顶层有 12 个承担内容或工程职责的目录，研究背景与组合原则同在 `config/`，组合记录分散在
`reviews/`、`data/`、`config/` 三处；同一个"当前版本"信息在 `current.md`、`status.json`、覆盖索引
和摘要中手工维护多处，已经出现不一致。

整理遵循两条原则：同一事实只手工维护一处；没有在用的结构优先退役，而不是补齐。

## 结果

- 内容收拢为 `research/`、`portfolio/`、`playbook/` 三个区；工程目录 `harness/`、`scripts/`、`tests/` 原地不动；
- 公司当前正文只由 `current.md` 指出；摘要只注明"本摘要基于"哪一版，索引不记录版本号；
- `status.json` 退役，其中的复核触发、关注主题与证据缺口迁入各公司 `tracking.md`（无 tracking 的迁入摘要）；
- `harness/research/`（研究状态 schema 与写入工具）删除；已有 `facts.jsonl`、`sources.json` 冻结保留；
  `harness/validation.py` 保留组合账本检查，研究侧只检查 `current.md` 指针；
- 两份研究索引合并为 `research/INDEX.md`；找不到原文的旧笔记列入缺档清单；
- 被替代的公司版本移入各公司 `archive/versions/`，已完成的单次报告移入 `archive/notes/`；
- `scripts/refresh_quotes.py` 在估值完整且拉取无报错时默认记录当日快照；`scripts/position_brief.py` 退役；
- 重复的架构与上下文说明合并：`context-policy.md` 并入 `architecture.md`，`retention.md` 并入 `portfolio-state.md`。

## 旧路径对照

数据库中旧事件的 `decision_ref`、`source_ref` 等引用保留整理前的原值，不批量改写审计历史。
需要找回材料时按下表换算：

| 整理前 | 整理后 |
|---|---|
| `coverage/` | `research/coverage/` |
| `coverage/COVERAGE_LOG.md`、`research_notes/KNOWLEDGE_INDEX.md` | `research/INDEX.md`（合并） |
| `research_notes/macro/` | `research/macro/` |
| `research_notes/` 其他笔记 | `research/topics/` |
| `config/research-context.md` | `research/context.md` |
| `config/principles.md`、`config/profile.json` | `portfolio/principles.md`、`portfolio/profile.json` |
| `reviews/REVIEWS_LOG.md` | `portfolio/LOG.md` |
| `reviews/decisions/`、`reviews/executions/` | `portfolio/decisions/`、`portfolio/executions/` |
| `reviews/portfolio/`、`reviews/holding-reviews/`、`reviews/portfolio_review_*.md` | `portfolio/reviews/YYYY/` |
| `reviews/daily/`、`reviews/suggest/`、`reviews/legacy/` | `portfolio/archive/` 下同名目录 |
| `reviews/LEDGER_CUTOVER.md`、`reviews/postmortems/legacy_data_lessons.md` | `portfolio/data/` |
| `data/investment.db` | `portfolio/data/investment.db` |
| `data/investment.backup_*.db` | `portfolio/data/backups/` |
| `data/*.png` | `portfolio/data/artifacts/` |
| `contracts/`、`workflows/`、`templates/` | `playbook/` 下同名目录 |
| `docs/migration.md` | `playbook/history/migration-2026-08.md` |
| `coverage/{SYMBOL}/status.json` | 退役；内容迁入该公司 `tracking.md` |

逐文件的移动清单、哈希与回退脚本保存在本地私有维护记录中，不进入公开仓库。

## 同日收尾复核

- 清理归档 README 和摘要中重复维护的当前版本入口，统一指向 `current.md`；删除已退役的 status 维护要求与研究结构状态说明。
- 活动时间线补齐 5 条已有记录，区分已成交、对账和统计复盘；修复能定位到原文的 3 条旧链接。
- 报价脚本在现金比例未知时正常输出；缺失报价或汇率时提示并拒绝快照；快照日期和备注统一采用北京时间，旧 `--record` 参数继续兼容。
- 修复期权行权测试对运行日期的依赖，增加缺失数据、北京时间午夜边界和旧参数回归测试；完整测试 **44 项全部通过**。
- 真实账本、原始来源、视觉资产和冻结事实记录保持原内容；原有重复快照警告、历史快照缺口与缺档线索留在私有维护记录中。

收尾前原件与差异也已保存，回退按备份恢复整理前工作区及用户原有未提交修改。
