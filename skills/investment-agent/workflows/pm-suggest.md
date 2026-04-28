# PM Suggest Workflow

## Goal

基于组合结构、policy 约束、coverage thesis 与 position metadata，生成一份可操作的组合级建议。

## Preconditions

- 组合中所有需要纳入 thesis-driven 判断的标的，最好都有 coverage
- `position_meta_tools.py` 已为主要持仓写入 metadata

## Preferred tools

```bash
python app/tools/portfolio_tools.py --refresh
python app/tools/pnl_tools.py --record --notes "suggest"
python app/tools/position_meta_tools.py read
python app/tools/policy_tools.py
```

## Steps

### 1. Coverage 与 metadata gate

先刷新组合状态并记录快照：

```bash
python app/tools/portfolio_tools.py --refresh
python app/tools/pnl_tools.py --record --notes "suggest"
```

然后读取 position metadata：

```bash
python app/tools/position_meta_tools.py read
```

检查：
- 若某持仓没有 coverage，明确标注该标的无法做 thesis-driven 建议
- 若 metadata 缺失或过旧，应先给出 warning

### 2. 读取完整组合状态

构建一个工作表，至少包含：
- symbol
- weight_pct
- current_price
- expected_cagr
- target_base
- risk_level
- ic_status
- theme_tags
- region
- sector
- growth_value

### 3. 运行 policy check

```bash
python app/tools/policy_tools.py
```

Policy 违规是硬约束，优先级高于其他建议。

如果组合里有 open sold puts，不要只看 `reserved_cash` 或 fully-assigned weight 这类静态数值；至少还要一起判断：
- `strike_gap`
- `moneyness`
- `days_to_expiry`
- 若现在平仓，大约要花多少钱

特别是像远 OTM、离到期仍有一段时间、且平仓成本已经很低的 put：
- 应更多视为“可选择提前回收的小尾部风险”
- 而不是直接表述成“当前有很大行权风险”

换句话说，agent 在解释层要区分：
1. contingent exposure 仍然存在
2. 但短期 assignment probability 可能已经明显下降
3. 是否提前平仓，取决于用户是否愿意用一小笔成本买确定性和流动性释放

### 4. 读取投资原则

读取：
- `config/principles.md`

用来框定：
- 选股原则
- 组合原则
- 调仓/离场原则

### 5. 先做组合级诊断，再做个股建议

组合级诊断建议至少包括：
- 主题敞口（theme cluster）
- 地区敞口（region exposure）
- 风格分布（growth / value / blend）
- IC 风险汇总（CLEAR / WATCHING / TRIGGERED）

### 6. 个股建议

对每个持仓，结合：
- 当前权重 vs thesis 目标权重
- expected_cagr
- risk_level
- ic_status
- policy 结果
- thesis 中的头寸管理原则

建议类型通常是：
- ADD
- HOLD
- TRIM
- EXIT
- UPDATE THESIS FIRST

### 7. 决策优先级

建议按以下顺序判断：
1. IC = TRIGGERED → 优先 EXIT / 明确减仓处理
2. Policy violation → 优先处理违规
3. 主题或个股明显过重 → TRIM
4. 低于目标权重且 CAGR / thesis 支撑强 → ADD consideration
5. 其余 → HOLD

### 8. Summary

结尾至少给出：
- Priority action
- Risk alerts
- Best opportunity

### 9. Archive

写入：
- `reviews/suggest/YYYY-MM-DD_suggest.md`
- 并更新 `reviews/REVIEWS_LOG.md`

## Notes

- 不要用成本价为 ADD / HOLD / EXIT 找理由
- 没有 CAGR 或 metadata 的标的，应先提示补研究而不是强行优化排序
- 对无 coverage 的持仓，可以给 rules-only 提示，但不要伪装成 thesis-driven 建议
