# 组合复盘

## 目标

检查敞口、现金、集中度、期权义务和需要投入研究注意力的事项，并在必要时回到完整公司研究。

## 上下文

加载：

- 来自 `harness.portfolio` 的当前组合状态；
- investor profile 和策略规则；
- 未关闭的期权敞口；
- 每个持仓 symbol 的研究导航 summary/status；
- 自上次 review 以来的近期 portfolio events。

摘要适合快速建立全局视图。某个 symbol 的风险或机会影响组合判断时，可以继续阅读完整
thesis、历史记录或 source documents，不需要另一个流程批准。

## 步骤

1. 检查 quote freshness，以及缺失的 FX/price 输入；
2. 计算权重、现金、或有期权敞口和策略信号；
3. 把每个持仓与研究状态连接：thesis version、last review、IC state、next trigger 和 evidence gaps；
4. 按证据/风险紧迫度排列关注事项，而不是按单日盈亏；
5. 对真正影响组合的 symbol 继续深入研究。

## 输出

归档一份简洁 review，包含 snapshot `as_of` 时间、数据质量提醒、敞口摘要、研究时效和下一步动作。Review 本身不代表要交易。
