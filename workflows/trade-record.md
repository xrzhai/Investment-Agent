# 交易记录

## 目标

记录已经在外部执行的交易，并更新结构化组合状态。

## 前提

- 已存在“已批准”的 decision reference，且文档标记为 `**状态：** approved`；baseline import 或明确修正除外；
- 执行证据包含稳定的 `execution_ref`、`symbol`、`side`、`quantity`、`price`、`fees`、`currency` 和执行时间。

## 步骤

1. 对照 decision 边界核验执行证据；
2. 通过 `PortfolioStore.record_trade` 记录交易，同时传入 `decision_ref` 和 `execution_ref`；该函数在一个事务中更新持仓、结算现金和 event log；
3. 入金/出金单独记录为 cashflows，不能重复记录交易结算款。期权事件使用对应的 option transition methods；
4. 生成新的 portfolio state 和 data-quality report；
5. 追加 execution note，并链接 decision 和生成的 event ID。

不能仅仅因为发生交易就重写 thesis。
