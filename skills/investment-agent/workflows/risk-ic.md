# Risk IC Sweep Workflow

## Goal

扫描所有已覆盖标的的 Invalidation Conditions，并给出每条 IC 的状态判断。

## Preferred tools

- `python app/tools/portfolio_tools.py --refresh`
- coverage thesis files under `coverage/{SYMBOL}/`
- 必要时补充公开市场数据源

## Steps

### 1. 获取持仓列表

```bash
python app/tools/portfolio_tools.py --refresh
```

### 2. 对每个有 coverage 的标的执行

若存在 `coverage/{SYMBOL}/current.md`：
1. 解析当前 thesis
2. 提取 Invalidation Conditions
3. 找到每条 IC 所需的可观察数据
4. 逐条判断状态：
   - `TRIGGERED`
   - `WATCHING`
   - `CLEAR`
   - `UNVERIFIABLE`

### 3. 输出排序

按严重程度排序：
- TRIGGERED first
- WATCHING second
- CLEAR last

每个标的至少展示：
- thesis 版本
- 每条 IC 的原文
- 关键数据点
- 当前判断

### 4. 升级规则

若任一 IC = `TRIGGERED`：
- 明确指出是哪条 IC 被触发
- 明确写出触发依据
- 立即建议运行 researcher update
- 不要用模糊措辞弱化问题

### 5. 注意事项

- 只有在 thesis 明确把价格写成 IC 时，价格下跌才算 IC 证据
- 对无法从公开数据直接验证的 IC，标为 `UNVERIFIABLE`
- 不要把“感觉不对”写成 TRIGGERED
