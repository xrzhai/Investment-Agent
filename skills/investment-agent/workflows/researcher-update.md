# Researcher Update Workflow

## Goal

基于新信息更新已有 coverage thesis，保留历史版本，并同步 position metadata。

## Preconditions

- `coverage/{SYMBOL}/current.md` 已存在
- 若不存在，应改走 initiate workflow

## Preferred tools

- `python app/tools/portfolio_tools.py --refresh`
- `python app/tools/position_meta_tools.py write ...`
- `python app/tools/position_meta_tools.py read {SYMBOL}`

## Steps

### 1. Pre-flight

检查 `coverage/{SYMBOL}/current.md`：
- 不存在：停止，提示先 initiate
- 存在：读取当前指针与当前 thesis

### 2. 识别更新触发器

若用户未提供，明确触发器属于哪类：
- earnings
- event
- quarterly
- ic
- other

### 3. 获取最新上下文

```bash
python app/tools/portfolio_tools.py --refresh
```

若更新涉及财报、估值或基本面，优先补充最新研究材料。

### 4. 更新 thesis，而不是重写 thesis

从当前版本出发，只改有实质变化的部分：
- 哪些 IC 状态变了？
- Fundamental 是被确认、削弱还是打破？
- Valuation 的 risk/reward 是否变化？
- Technical / flows 是否明显变化？
- 当前权重下的头寸管理原则是否仍成立？

不要在没有新证据时重写整篇 thesis。

### 5. 覆盖历史必须诚实

追加一行覆盖历史，至少说明：
- 这次为什么更新
- 原判断哪里对了
- 哪里错了
- 这次修正了什么

### 6. 保存新版本

- 保存为 `coverage/{SYMBOL}/v{N}_YYYY-MM-DD.md`
- 更新 `coverage/{SYMBOL}/current.md`
- 更新 `coverage/COVERAGE_LOG.md`

### 7. 同步 position metadata

更新至少以下字段：
- `ic-status`
- valuation scenario targets / probabilities（如果变了）
- `theme-tags`（如果 thesis 暴露变化）
- 其他分类字段仅在有实质变化时更新

命令形式：

```bash
python app/tools/position_meta_tools.py write {SYMBOL} \
  --target-bear ... --target-base ... --target-bull ... \
  --prob-bear ... --prob-base ... --prob-bull ... \
  --horizon-months ... \
  --sector ... --region ... --cap-style ... \
  --growth-value ... \
  --theme-tags '[...]' \
  --risk-level ... --ic-status ...
```

### 8. 验证

```bash
python app/tools/position_meta_tools.py read {SYMBOL}
```

如果本次更新触及 valuation，继续遵守：
- `eps_forward` 交叉验证
- ADR 比率慎用或手算
