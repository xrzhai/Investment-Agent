Record an Agent operational mistake into the Mistake Memory system.

Use this when the user points out that the Agent made an error, or when you detect a mistake that should be remembered to avoid recurrence.

## Step 1 — Collect incident information

Ask the user (or infer from context) the following. You do NOT need to ask all as separate questions — gather from the current conversation if already clear:

- **What happened?** Brief description of the mistake
- **Task scope:** Which command/task was running? (e.g. `researcher_update`, `pm_suggest`, `pm_daily`, `researcher_initiate`, `any`)
- **Symbol:** Which symbol was involved? (leave empty if portfolio-wide / not symbol-specific)
- **Impact:** What went wrong as a result? (optional)

## Step 2 — Classify and draft

Classify the mistake into one of these types:

| mistake_type | When to use |
|---|---|
| `data` | Misread or misinterpreted a data field (yfinance, DB, markdown) |
| `calculation` | Wrong formula, wrong units, wrong denominator |
| `logic` | Recommendation contradicted own thesis, IC status, or principles |
| `omission` | Skipped a required step (e.g. forgot to load coverage before analyzing) |
| `format` | Output structure broken (table alignment, markdown nesting, unit labeling) |

Then draft the 4 core fields:

- **mistake**: What went wrong, in one concrete sentence
- **root_cause**: Why it happened (the underlying cause, not just the symptom)
- **prevention_rule**: Specific, actionable rule to prevent recurrence (start with a verb: "Always...", "Before...", "Never...")
- **trigger_check**: When should this check fire? ("When running {task}, before {action}, verify {condition}")

Also set:
- **severity**: `high` (silently gave wrong data/recommendation) | `medium` (user noticed, output was incorrect) | `low` (cosmetic/formatting)
- **confidence**: Start at `0.7` for user-reported, `0.5` for self-detected

## Step 3 — Show draft and confirm

Present the draft to the user in this format:

```
📝 Mistake Memory 草稿

类型: {mistake_type} | 严重度: {severity} | 任务: {task_scope or "any"} | 标的: {symbol_scope or "通用"}

错误: {mistake}
根因: {root_cause}
预防规则: {prevention_rule}
触发检查: {trigger_check}
影响: {bad_outcome or "—"}
```

Ask: "确认写入？可以直接修改任何字段后告诉我。"

## Step 4 — Write to DB

Once confirmed, build the JSON payload and pipe to the tool:

```
echo '{...json...}' | /c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/postmortem_tools.py --create
```

The JSON must contain:
```json
{
  "mistake_type": "...",
  "task_scope": "...",
  "symbol_scope": "...",
  "mistake": "...",
  "root_cause": "...",
  "prevention_rule": "...",
  "trigger_check": "...",
  "severity": "...",
  "confidence": 0.7,
  "source": "user_report",
  "bad_outcome": "..."
}
```

Set `task_scope` to `null` (not the string "null") if not task-specific.
Set `symbol_scope` to `null` if not symbol-specific.

## Step 5 — Confirm and prompt next step

On success, output:

```
✅ 已写入 Mistake Memory（草稿，ID: {id}）

状态: draft — 尚未激活
运行 /postmortem:list 查看并激活此条目。
```
