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
