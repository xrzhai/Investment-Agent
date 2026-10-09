# Portfolio：原则、记录与账本

本区回答"组合现在是什么状态，为什么行动，结果与约束是什么"。公司本身的商业与估值判断在
[`research/`](../research/README.md)。

```text
portfolio/
  LOG.md          组合活动时间线：复盘、决策、执行、对账与重要研究更新（私有）
  principles.md   投资原则与风险边界
  profile.json    结构化组合偏好（集中度、现金下限等）
  reviews/YYYY/   组合复盘、持仓复盘、对账与收益重建（私有）
  decisions/      决策理由与用户授权（私有）
  executions/     成交证据与记账说明（私有）
  data/           SQLite 账本、历史备份、账本边界说明与附件（私有，见 data/README.md）
  archive/        已退出工具的历史输出：daily/、suggest/、legacy/（私有）
```

## 事实从哪里来

- **当前组合事实以 `data/investment.db` 为准**，通过 `harness.portfolio` 读取和写入，不用临时 SQL；
- 报价只用 `scripts/refresh_quotes.py` 刷新，估值完整且拉取无报错时自动记录当日快照；
- `LOG.md` 是时间线，不复制最新持仓，也不把旧建议改写成当前判断。

## 阅读历史记录时

Agent 可以在需要理解决策演化、行为偏差、组合约束或历史假设时阅读这些记录。历史仓位和
prior recommendation 不是当前公司事实，使用时应注明时间和角色。

真正的成交记录需引用用户批准的 decision 和外部 execution evidence。历史 Markdown 不回放成
新的组合事件。数据库中旧事件的 `decision_ref` 等引用可能仍是 2026-10-09 整理前的路径
（如 `reviews/decisions/...`），保留原值作为审计历史；对照表见
[`playbook/history/2026-10-reorganization.md`](../playbook/history/2026-10-reorganization.md)。

真实组合记录与数据库默认保留在本地并由 `.gitignore` 排除。
