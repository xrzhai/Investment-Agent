# Options Record Workflow

## Goal

记录美股 short cash-secured puts，并把它们作为组合内的 contingent exposure 纳入系统管理。

## 当前范围

仅支持：
- 美股 short puts
- 现金担保（cash-secured）口径
- open / assigned / expired / closed 状态
- underlying 现价辅助判断（若可取得）

不支持：
- 多腿策略
- Greeks
- 复杂保证金模型
- 期权链实时估值依赖

## Preferred tools

- `python app/tools/option_tools.py list`
- `python app/tools/option_tools.py summary`
- `python app/tools/option_tools.py open-put ...`
- `python run.py options list`
- `python run.py options summary`
- `python run.py options open-put ...`

## Minimal input format

推荐至少提供：
- underlying
- expiry_date
- strike
- contracts
- premium

示例：

```bash
python run.py options open-put PDD 2026-09-18 95 -1 --premium 7.73
```

语义约定：
- `contracts` 接受 `-1/-2` 风格输入，但系统内部会按 short contract count 的正数存储
- `reserved_cash = strike * contracts * 100`
- `effective_entry_if_assigned = (gross obligation - premium + fees) / total_shares`

## Notes

- `reserved_cash` 是压力测试 / 名义承诺口径，不等于当前 `CASH_USD` 必须完全覆盖
- premium 属于组合内部现金流，不是外部 `cashflow_events`
- 若卖 put 后权利金到账但尚未反映到 `CASH_USD`，应直接更新 `CASH_USD`，不要记成外部入金
