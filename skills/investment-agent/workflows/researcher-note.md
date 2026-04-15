# Researcher Note Workflow

## Goal

把一次研究事件或观察记录进 journal research notes，供后续分析和建议流程引用。

## Typical note types

- `earnings`
- `dcf`
- `comps`
- `note`

## Preferred CLI

```bash
python run.py journal research {SYMBOL} --type {TYPE} --content "{CONTENT}"
```

## Steps

### 1. 确认 SYMBOL

如果未提供，先明确是哪个标的。

### 2. 确认 note type

在 `earnings / dcf / comps / note` 中选一个。

### 3. 准备内容

鼓励记录：
- 具体数字
- 关键结论
- 触发判断变化的原因

避免只写模糊描述，如：
- “业绩很好”
- “市场反应一般”

### 4. 写入 journal

```bash
python run.py journal research {SYMBOL} --type {TYPE} --content "{CONTENT}"
```

### 5. 告知后续用途

研究笔记可被后续流程引用，例如：
- 单标的深度分析
- 组合建议
- thesis update 前的上下文补充

## Notes

- 建议一个事件一条 note，不要把多个事件混成一条
- 如果研究结论已经足以改变 thesis，应继续走 `researcher-update.md`
