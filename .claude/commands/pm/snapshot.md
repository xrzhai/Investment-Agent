Show a quick portfolio snapshot using cached prices (no market data refresh).

## Step 1 — Get portfolio state

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/portfolio_tools.py
```

(No `--refresh` — this uses the last stored prices.)

## Step 2 — Output

Present a compact table. No analysis, no recommendations — pure data.

```
Portfolio Snapshot — {timestamp of last price update}
─────────────────────────────────────────────────────────────────
Symbol   Shares   Price      Weight    Day P&L    Total P&L
NVDA     50       $875.20    22.4%     +$412      +$8,240 (+12.1%)
META     30       $520.50    18.1%     -$180      +$3,900 (+8.3%)
...
─────────────────────────────────────────────────────────────────
Total    —        —          100%      +$XXX      +$XX,XXX (+X.X%)
Portfolio Value: $XXX,XXX
```

If the last price update is more than 24 hours old, add a note: "⚠ Prices last updated {N} hours ago. Run `/pm:daily` for live prices."
