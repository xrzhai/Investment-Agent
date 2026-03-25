Run a self-audit against historical Agent mistakes before finalizing an output.

Use this when the user asks "check your work", "have you made this mistake before", or when you want to self-verify before delivering a result.

## Step 1 — Identify context

Determine from conversation context (or ask the user if unclear):
- **task_scope**: What task was just performed? (e.g. `researcher_update`, `pm_suggest`, `pm_daily`, `researcher_initiate`, `any`)
- **symbol**: Which symbol, if any? (or blank for portfolio-wide tasks)

## Step 2 — Recall relevant mistakes

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/postmortem_tools.py --recall --task {task_scope} [--symbol {symbol}]
```

If the result is an empty list `[]`:
```
✅ 历史错误自查：无相关记录
暂无与此任务相关的历史错误教训。
```
Stop here.

## Step 3 — Build self-audit checklist

Format the recalled entries as a checklist:

```
⚠️ 历史错误自查清单（{N} 条相关教训）
任务: {task_scope} | 标的: {symbol or "通用"}
────────────────────────────────────────────

[ ] [{mistake_type}] {trigger_check}
    规则: {prevention_rule}

[ ] [{mistake_type}] {trigger_check}
    规则: {prevention_rule}

...
```

## Step 4 — Audit the current output

For each checklist item, examine the current work/output and determine:

- ✅ **已规避**: The prevention rule was followed correctly
- ❌ **疑似存在**: The same mistake pattern may be present
- ⚪ **不适用**: This check doesn't apply to the current output

Replace each `[ ]` with the appropriate symbol and add a one-line note:

```
✅ [data] yfinance eps_forward 年份校验
   → 已确认使用 trailing EPS，非 forward 字段

❌ [logic] IC 状态与建议一致性
   → 发现 601899.SH IC=WATCHING 但建议为 ADD，需修正

⚪ [calculation] CAGR 公式月/年单位
   → 本次未涉及 CAGR 计算
```

## Step 5 — Correct and re-output if needed

If any ❌ items found:
1. Identify the specific part of the output that violates the rule
2. Correct it
3. Re-present the corrected section with a note:

```
🔧 已修正：{brief description of what was fixed}
```

If all items are ✅ or ⚪:
```
✅ 自查完成，未发现历史错误模式。
```

## Step 6 — Prompt to log new mistakes

If the audit revealed a new mistake pattern not in the list, prompt:

```
💡 发现新的错误模式？运行 /postmortem:create 记录下来。
```
