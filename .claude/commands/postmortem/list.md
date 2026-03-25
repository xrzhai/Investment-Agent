List and manage all Mistake Memory entries.

## Step 1 — Load all entries

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/postmortem_tools.py --list
```

## Step 2 — Display by status group

Format the output as three sections. Only show sections that have entries.

### 草稿（Draft）— 待审核

```
ID   类型         严重度   任务范围         错误摘要
──────────────────────────────────────────────────────
{id} {type}      {sev}   {task_scope}    {mistake[:60]}
...
```

For each draft, append:
```
→ 激活: /postmortem:approve {id}  |  忽略: /postmortem:retire {id}
```

### 已激活（Active）— 生效中

Same table format. For each active entry, show:
```
[{mistake_type}] {trigger_check}
→ 规则: {prevention_rule}
```

### 已归档（Retired）— 不再使用

Just the table, no action prompts.

## Step 3 — Summary line

```
共 {N} 条记录：{n_draft} 草稿 / {n_active} 激活 / {n_retired} 归档
```

If there are draft entries, remind:
```
⚠️ 有 {n_draft} 条草稿未审核。激活后才会在 /postmortem:check 中生效。
```

If there are zero active entries:
```
ℹ️ 暂无激活的错误记忆。使用 /postmortem:create 记录第一条教训。
```
