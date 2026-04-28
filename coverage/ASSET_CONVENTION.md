# Coverage Asset Convention

适用范围：`coverage/{SYMBOL}/` 下的图表、图片、HTML artifact。

目标：
- `md` 是主入口
- 图片路径稳定
- 默认轻量，按需补图

## 目录

```text
coverage/{SYMBOL}/
  current.md
  vN_YYYY-MM-DD.md
  assets/
    current/
      overview.png
      annual-trends.png
      quarterly-trends.png
      valuation-snapshot.png
      price-position.png
      dashboard.html
    archive/
      YYYY-MM-DD/
        ...same files
```

含义：
- `assets/current/`：当前有效图表包，供 markdown 引用
- `assets/archive/YYYY-MM-DD/`：重要版本快照；非必要不归档

## 默认规则

1. markdown 永远引用 `assets/current/`
   - 例：`![Valuation](assets/current/valuation-snapshot.png)`
2. 新图默认覆盖 `current/` 中同名文件
3. 只有重要财报 / thesis 明显变化 / 对外输出时，才复制到 `archive/YYYY-MM-DD/`
4. 不在 `current/` 文件名里加版本号

## 推荐文件名

| 文件名 | 用途 |
|--------|------|
| `overview.png` | 一张总览图 |
| `annual-trends.png` | 3-5 年趋势 |
| `quarterly-trends.png` | 4-6 季趋势 |
| `valuation-snapshot.png` | 估值与目标区间 |
| `price-position.png` | 价格、均线、thesis 区间 |
| `dashboard.html` | 可选的交互页 |

规则：
- 全部小写
- kebab-case
- 版本信息放在 archive 目录，不放在 current 文件名

## 轻量默认集

默认优先级：
1. 先给 `overview.png` 或 `valuation-snapshot.png`
2. 讲趋势时，再补 `annual-trends.png` 或 `quarterly-trends.png`
3. 讲价格位置时，再补 `price-position.png`

也就是：
- 默认 1 张图起步
- 常见情况 1-2 张图就够
- 不默认一次性生成完整图包
