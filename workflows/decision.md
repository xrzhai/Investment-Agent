# 仓位决策

## 目标

决定是否新建、加仓、持有、减仓或退出单一仓位。

## 上下文

仓位决策通常会结合两个事实域：

- 一个 symbol 的当前 thesis、相关 facts 和 source metadata；
- 当前组合状态、现金、敞口和策略约束；
- 如果存在，读取同一个未完成动作之前已批准的 decision。

历史版本、相关公司和过去 review 在能解释当前判断时都可以阅读；注意区分历史语境与当前证据。

## 建议记录

1. **研究证据**：thesis version、facts、证伪条件和不确定性；
2. **组合约束**：当前/或有权重、现金、集中度和替代方案；
3. **决策**：动作、规模边界、价格/条件边界和有效期；
4. **反证**：什么证据会取消该动作；
5. **执行边界**：明确说明这不是 execution record。

可以使用 decision template 保存到 `reviews/decisions/`。推理仍在讨论时保持 `draft`；只有
用户明确批准后才把 status 改为 `approved`。Agent 生成的 decision 不能自动批准自己。
