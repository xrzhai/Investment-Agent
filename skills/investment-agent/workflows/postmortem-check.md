# Postmortem Check Workflow

## Goal

在交付结果前，基于历史 Mistake Memory 做一次自查，避免重复犯错。

## When to use

- 用户要求“检查一下你的结果”
- 当前任务属于高风险输出
- 任务模式看起来和以前犯过错的场景相似

## Preferred tool

```bash
python app/tools/postmortem_tools.py --recall --task {task_scope} [--symbol {symbol}]
```

## Steps

### 1. 确定上下文

先识别：
- `task_scope`
- `symbol`（如适用）

### 2. 召回相关历史错误

运行 recall。

若结果为空：
- 明确告诉用户暂无相关历史教训
- 可直接结束

### 3. 形成 checklist

把 recall 结果转成自查清单。
每条至少包括：
- `mistake_type`
- `trigger_check`
- `prevention_rule`

### 4. 对当前输出逐条审计

每条检查项应被判定为：
- `已规避`
- `疑似存在`
- `不适用`

### 5. 若发现问题，先修正再输出

如果发现 `疑似存在`：
- 明确指出是输出的哪一部分违反了历史规则
- 先修正
- 再告知用户已修复

### 6. 若发现新的错误模式

如果这次暴露的是一个历史库里没有的新错误模式：
- 建议补一条新的 postmortem 记录
