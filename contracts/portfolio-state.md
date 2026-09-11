# 组合状态契约

## 范围

组合管理是必要但低频的职能。系统优先保证正确性和可审计性，而不是服务高频交易。

## 结构化事实

SQLite 保存：

- 当前持仓读取模型；
- 追加式 portfolio events；
- 现金流事件（cashflow events）；
- 期权合约及其状态变化；
- 带来源的报价观察；
- 组合快照；
- 持久化的 instrument classifications，包括 sector、region、style、themes 和 risk label，用于敞口汇总。

研究文档不能把实时数量、成本或盈亏作为 canonical facts。Instrument classifications 独立于当前持仓行保存，因此平仓不会抹掉可复用的敞口 metadata。

## 事件记录规则

以后每一次状态变更都应生成事件，并包含：

- 稳定的 `event_id`；
- `event_type`；
- `occurred_at`；
- 适用时记录受影响的 symbol；
- 结构化 payload；
- `source` 和可选的 `source_ref`；
- `recorded_at`。

对于股票和期权成交，event ID 从稳定的外部 `execution_ref` 派生。重复提交同一执行记录时，应在任何现金或持仓变更前拒绝该请求。独立的 `decision_ref` 用来保留“为什么决策”和“是否执行”之间的边界。

外部入金与出金同样需要稳定的 `cashflow_ref`，防止 Agent 重试时重复记账。

现金流同时记录本币和组合基准币两个金额：`amount_local` + `currency` 表示实际现金变动，`amount_base` + `fx_rate_to_base` 表示按事件时点 FX 换算的 USD 金额。`amount_usd` 保留为兼容字段，但语义与 `amount_base` 相同，不能把 CNY 本币金额直接写入。

`flow_scope` 区分 `external` 和 `internal`：只有外部入金/出金参与 TWR 的现金流中性化，组合内部换汇、资产间转移或其他内部调拨不参与；内部操作仍保留事件审计轨迹。外部现金流缺少事件时点基准币金额时，应停止或标记 TWR 计算，不能用当前 FX 静默回填。

持仓行是当前读取模型，events 提供审计轨迹。

普通股票成交应在一个事务内同时更新相关持仓、结算币种现金和 event log。卖出 put 的开仓、平仓和行权也应原子更新合约状态以及相关现金/持仓读取模型。外部入金和出金使用 cashflow records，不能重复记录交易结算现金。

## 报价记录规则

价格不只是一个数字。记录报价时应保存：

- `symbol`；
- price 和 currency；
- 市场 `as_of` 时间；
- `provider` / `source`；
- 可选的 source reference；
- 获取时间 `retrieved_at`。

FX 使用 canonical quote symbol `FX:{LOCAL}/{BASE}`，含义是一单位 local currency 对应多少 base currency，并沿用同样的 `as_of` 与来源规则。Quote time 必须带时区。查询历史状态时，只选择不晚于 cutoff 的观察值；超过 freshness window 的价格或 FX 要标为 stale，不能静默伪装成当前值。

研究估值仍需要研究级 source records；组合报价不会自动成为 thesis 证据。

## 使用原则

- 公司商业判断不应把个人成本或盈亏当作基本面证据；
- Portfolio review 可以使用权重、现金、敞口和策略信号；
- Decision 要把研究证据和组合约束分开呈现；
- Trade record 必须引用已批准的 decision，明确修正或初始 baseline 除外。
