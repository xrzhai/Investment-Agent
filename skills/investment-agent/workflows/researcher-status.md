# Researcher Status Workflow

## Goal

查看整个组合的 coverage 完成度、更新时效和需要优先补的研究对象。

## Preferred tool

```bash
python app/tools/portfolio_tools.py
```

配合读取：
- `coverage/{SYMBOL}/current.md`
- `coverage/COVERAGE_LOG.md`

## Steps

### 1. 读取组合持仓

```bash
python app/tools/portfolio_tools.py
```

这里只是状态检查，不一定需要刷新价格。

### 2. 检查每个持仓的 coverage 状态

对每个持仓：
- 是否存在 `coverage/{SYMBOL}/current.md`
- 当前版本号和日期是什么
- 距今多久未更新

### 3. 输出状态表

建议至少包含：
- Symbol
- Weight%
- Version
- Last Updated
- Age(days)
- Status

状态可分为：
- Current
- NO COVERAGE
- STALE
- CHECK IC

### 4. 输出优先级建议

最多列 3 条：
- 哪个标的最该 initiate
- 哪个标的最该 update
- 哪个标的需要先做 IC 检查

## Notes

- 这是 coverage 管理视角，不是买卖建议视角
- 不必强制刷新价格；关键是 coverage 完整性和时效性
