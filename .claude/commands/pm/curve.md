Display the portfolio P&L curve: capital curve (USD) and cumulative time-weighted return (TWR %).

Run:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --curve
```

To limit to the last N days, append `--days N`. For example, last 90 days:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --curve --days 90
```

The chart displays directly in the terminal as ASCII lines. If fewer than 2 snapshots exist, the tool will prompt you to run `/pm:daily` or `/pm:suggest` first to accumulate data.
