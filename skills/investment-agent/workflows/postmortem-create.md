# Postmortem Create Workflow

## Goal

把一次 agent 操作错误记录进 Mistake Memory，形成可复用的预防规则。

## When to use

- 用户指出 agent 刚刚犯了错
- agent 自己发现这次输出存在明确错误模式
- 一个错误值得被长期记住，避免再次发生

## Preferred tool

```bash
python app/tools/postmortem_tools.py --create
```

JSON 从 stdin 传入。

## Steps

### 1. 收集 incident 信息

优先从当前对话中获取；不足时再问用户。至少弄清：
- 发生了什么错误
- task scope（如 `researcher_update`、`pm_suggest`、`any`）
- symbol（如有）
- 影响是什么（可选）

### 2. 分类

选择一种 `mistake_type`：
- `data`
- `calculation`
- `logic`
- `omission`
- `format`

### 3. 起草 4 个核心字段

- `mistake`：错误本身，单句、具体
- `root_cause`：根因，不只是表面症状
- `prevention_rule`：可执行的预防规则，最好以 “Always / Before / Never ...” 开头
- `trigger_check`：这个检查何时应该触发

同时补齐：
- `severity`
- `confidence`
- `source`
- `bad_outcome`

### 4. 向用户展示 draft

在写入前先给出草稿，允许用户改字段。

### 5. 写入 DB

命令模式：

```bash
echo '{...json...}' | python app/tools/postmortem_tools.py --create
```

JSON 需包含：
- `mistake_type`
- `task_scope`
- `symbol_scope`
- `mistake`
- `root_cause`
- `prevention_rule`
- `trigger_check`
- `severity`
- `confidence`
- `source`
- `bad_outcome`

### 6. 结果说明

成功后应明确告诉用户：
- 已写入 draft
- 还未激活
- 需要再通过 list / approve 流程激活
