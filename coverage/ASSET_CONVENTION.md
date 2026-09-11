# 公司研究视觉资产约定

适用范围：`coverage/{SYMBOL}/` 下的图表、图片和 HTML artifact。

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
      dashboard.html
    archive/
      YYYY-MM-DD/
      ...同名文件
```

含义：
- `assets/current/`：当前有效图表包，供 markdown 引用
- `assets/archive/YYYY-MM-DD/`：重要版本快照；非必要不归档

## 默认规则

1. markdown 永远引用 `assets/current/`
   - 例：`![估值](assets/current/valuation-snapshot.png)`
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
| `dashboard.html` | 可选的交互页 |

规则：
- 全部小写
- 使用 kebab-case
- 版本信息放在 `archive/` 目录，不放在 `current/` 文件名

## 是否需要图

图表不是 coverage 的必需品。只有当它能明显帮助理解商业机制、长期财务趋势或估值时
才创建；数量和形式由研究问题决定，不默认生成完整图包。
