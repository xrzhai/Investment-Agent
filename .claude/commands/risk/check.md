Run a policy check on the current portfolio against the investor's rules.

## Steps

1. **Run policy check**:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/policy_tools.py
```

2. **Present the results**:
   - State clearly: **PASS** or **VIOLATIONS FOUND**
   - For each violation: what rule, current value, threshold, and what to consider doing
   - List the active rules being checked (from `profile_rules` in the output)

3. **If violations exist**: add at the end — "Run `/pm:suggest` for specific rebalancing recommendations that resolve these violations."

Keep it brief and direct. If no violations, say so plainly.
