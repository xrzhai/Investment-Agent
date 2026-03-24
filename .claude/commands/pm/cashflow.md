Record a cash deposit or withdrawal event (used for accurate TWR calculation).

Arguments provided by the user:
- AMOUNT: dollar amount in USD — positive for deposit, negative for withdrawal
- DESC (optional): one-line description of the event

Ask the user for AMOUNT and DESC if not provided as arguments.

Run:

```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --cashflow {AMOUNT} --desc "{DESC}"
```

The tool will automatically record a pre-cashflow snapshot to establish a clean TWR sub-period boundary before writing the event.

Example: user deposits $5,000
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --cashflow 5000 --desc "新增资金"
```

Example: user withdraws $2,000
```
/c/Users/zhaix/miniconda3/envs/work/python.exe app/tools/pnl_tools.py --cashflow -2000 --desc "取出资金"
```
