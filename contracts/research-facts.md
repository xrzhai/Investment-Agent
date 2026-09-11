# 研究事实与来源约定

## 先决定是否需要结构化

Markdown 可以直接承载研究。探索性笔记、公司理解、类比、反方观点和未完成想法，
不需要为了进入 Harness 而拆成 JSON。

当一条信息需要跨任务复用、按日期筛选、追踪更新或反复核验时，可以使用：

```text
coverage/{SYMBOL}/
├─ current.md          # 当前 thesis 指针，可选但推荐
├─ vN_YYYY-MM-DD.md    # 版本化 thesis
├─ summary.md          # 导航摘要，可选
├─ status.json         # 当前状态，可选
├─ facts.jsonl         # 值得复用的原子事实，可选
├─ sources.json        # 与 facts 对应的来源登记，可选
└─ source_docs/        # 本地来源材料，可选
```

Legacy coverage 可以保持原样。结构化应随着真实使用逐步发生，不批量制造 placeholder。

## 来源记录

使用 `sources.json` 时，每条 source 至少应让下一位 Agent 能找到并判断它：

- 稳定的 `source_id`；
- 标题、publisher 和来源类型；
- 发布时间，或日期未知的原因；
- URL 或 coverage 目录内的 `local_path`；
- 是否属于一手来源；
- 必要时写明适用范围和局限。

本地路径不能逃逸 symbol 目录。Raw source 不静默覆盖；修正时保留新的记录和原因。

## 原子事实

只有值得复用的 claim 才进入 `facts.jsonl`。使用该文件时，一条记录通常包括：

- `fact_id`、`symbol`、`fact_key` 和自然语言 `statement`；
- `fact_type`：`reported`、`guidance`、`consensus`、`assumption` 或 `inference`；
- `source_ids`、`recorded_at`；
- 适用时补充 `period`、`as_of`、`available_at`、`value`、`unit`、`locator`；
- 需要保留冲突或演化时使用 `status` 和 `supersedes`。

事实记录是检索辅助，不是写作素材清单。Thesis 可以直接引用来源或用自然语言综合，
不要求每一句判断都有 fact ID。

## 使用原则

- 区分来源报告的事实、管理层说法、市场预期、分析假设和推断；
- 比较不同期间或口径时把差异说清楚；
- 旧记录可以保留，新的估计通过新记录说明变化，不静默改写历史；
- prior Agent output 和旧 thesis 可以提供思考语境，但不能单独证明当前事实；
- 缺失或冲突直接说明，不为了 schema 完整而补猜测。

## 估值

估值属于公司研究，与个人成本和仓位无关。

- 价格、股本、净现金/净负债和 enterprise value 注明观察日期与来源；
- 使用 consensus 时写清 provider、retrieval date 和 fiscal period；
- 折现率、terminal assumptions、multiples 和情景增长是分析假设；
- owner earnings、DCF、SOTP、单位经济性或反向估值都可以，方法应适应生意；
- 重点解释当前价格隐含什么、回报从哪里来，以及什么会使判断失效；
- 输入不足时可以只保留框架和疑问，不沿用过期目标价。
