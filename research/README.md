# Research：公司研究、专题与宏观

本区回答"这家公司或机制如何运作，价值如何形成，当前证据支持什么判断"。估值属于这里；
个人数量、成本、盈亏和仓位属于 [`portfolio/`](../portfolio/README.md)。

```text
research/
  INDEX.md            研究导航：公司 coverage、专题、宏观、缺档线索（私有）
  context.md          用户的研究思想与价值投资背景
  coverage/{SYMBOL}/  公司研究（私有）
    current.md        唯一的当前版本指针：一行正文文件名
    vN_YYYY-MM-DD.md  当前正文（或 memo.md），留在公司根目录
    summary.md / README.md / tracking.md   摘要、导航与持续验证点，按需
    research_notes/   公司专属补充分析与跟踪笔记，按需
    source_docs/      原始来源；assets/ 配图（见 coverage/ASSET_CONVENTION.md）
    archive/          versions/ 被替代版本；notes/ 已完成的单次报告
  topics/             跨公司专题、类比与未成熟想法（私有）
  macro/              中美宏观月度观察与半年复核（私有）
```

目录按需创建，不预先补齐。

## 版本与时点

- 当前正文只由 `current.md` 指出。摘要、索引不写"当前是哪一版"；摘要可以注明"本摘要基于"
  哪一版，若与 `current.md` 不一致，说明摘要需要随新版本更新；
- 研究日期、财务截至期和估值参考日写在正文开头，不从文件名推导；
- 部分公司保留的 `facts.jsonl`、`sources.json` 是冻结的历史记录，可直接阅读；新研究不要求补充。

## 阅读专题与旧笔记时

Agent 可以根据问题自由搜索和阅读原文。索引、日期、symbols 和 tags 只是导航工具，
不是读取许可或固定入口。使用这些材料时注意区分：

- 当时观察到的事实；
- 作者或 Agent 当时的判断；
- 可以继续泛化的机制；
- 需要回到原始来源刷新后才能用于当前 coverage 的 claim。

旧笔记不要求统一改成 JSON 或补齐 front matter。新的 idea 也可以直接写自然 Markdown。
专题中可以包含与组合、行为或决策有关的思考；它们不是公司基本面的 primary evidence，
但在问题相关时不需要被程序隐藏。

真实研究内容默认保留在本地并由 `.gitignore` 排除。
