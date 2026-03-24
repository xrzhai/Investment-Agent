# Investment Agent

个人投资 Copilot，为长期持仓美股投资者设计。

以 Claude Code 为主接口，CLI 为辅助。所有数值计算由 Python 确定性完成，LLM 仅负责解释、摘要与建议文字化。所有建议仅供参考，无自动执行。

---

## 核心功能

- **持仓管理** — 手动录入或 CSV 批量导入，yfinance 实时价格，PnL / 权重计算
- **规则检查** — 集中度上限、禁止标的等 policy 自动检测
- **Coverage 系统** — 为每支持仓维护三维度结构化投资论点（Fundamental / Valuation / Technical + IC + 头寸管理），版本历史保留
- **Position Metadata** — 每支持仓的量化 metadata：Bear/Base/Bull 目标价、期望 CAGR、主题标签、风险等级、IC 状态
- **组合建议** — 基于主题敞口聚类、CAGR 排序、thesis 头寸规则的可操作建议，自动存档
- **投资日志** — 建仓论点、操作记录、LLM 建议统一归档

---

## 快速开始

```bash
# 环境：conda work（Python 3.12）
cd "g:/我的云端硬盘/03_Work/Projects/Investment-Agent"

# 导入持仓（CSV 格式：symbol,quantity,avg_cost）
python run.py portfolio import portfolio.csv

# 初始化投资者配置
python run.py profile init

# 刷新价格 + 保存快照
python run.py portfolio refresh

# 查看持仓
python run.py portfolio summary

# 规则检查
python run.py portfolio check
```

在 Claude Code 中直接使用 slash commands（主要工作流）：

```text
# 组合管理
/pm:daily         # 完整日检（持仓 + 规则 + 分析）
/pm:suggest       # 组合诊断 + 个股建议（自动存档至 reviews/）
/pm:snapshot      # 快速持仓快照（不刷新价格）

# 风险管理
/risk:check       # policy 规则检查
/risk:ic          # Invalidation Conditions 扫描

# Coverage 工作流（投资论点管理）
/researcher:initiate NVDA   # 发起覆盖（新建 thesis）
/researcher:update NVDA     # 更新覆盖（财报后 / 事件驱动）
/researcher:analyze NVDA    # 单持仓深度分析
/researcher:note NVDA       # 记录研究笔记
/researcher:status          # 全组合覆盖状态一览
```

---

## 持仓 CSV 格式

```csv
symbol,quantity,avg_cost
NVDA,110,145.10
META,28,700.32
GOOGL,35,312.60
```

文件放在项目根目录，运行 `python run.py portfolio import portfolio.csv` 导入。

---

## 项目结构

```
investment-agent/
├── run.py                          # CLI 入口
├── app/
│   ├── cli/                        # CLI 命令层
│   ├── engines/                    # 业务逻辑（deterministic，无 I/O）
│   ├── services/                   # 外部集成（yfinance、Claude API）
│   ├── repositories/               # SQLite CRUD
│   ├── models/                     # Pydantic domain models + SQLModel 表
│   ├── prompts/                    # LLM prompt 模板
│   └── tools/                      # Claude Code 调用脚本（JSON 输出）
│       ├── portfolio_tools.py      # 持仓状态 + 实时价格
│       ├── policy_tools.py         # policy 规则检查
│       └── position_meta_tools.py  # position metadata 读/写
├── coverage/                       # 投资论点（每支股票一个子目录）
│   ├── COVERAGE_LOG.md             # 10 个标的覆盖状态一览
│   ├── COVERAGE_WORKFLOW.md        # 核心工作流规范
│   ├── THESIS_TEMPLATE.md          # 三维度论点模板
│   └── {SYMBOL}/
│       ├── vN_YYYY-MM-DD.md        # 历史版本（不覆盖，递增保留）
│       └── current.md              # 一行指针，指向当前生效版本
├── reviews/                        # 组合级分析存档（与 coverage 平行）
│   ├── REVIEWS_LOG.md              # 所有运行记录索引
│   ├── suggest/                    # /pm:suggest 输出存档
│   │   └── YYYY-MM-DD_suggest.md
│   └── daily/                      # /pm:daily 输出（预留）
├── config/
│   ├── profile.json                # 投资者配置（风格/风险容忍/仓位上限）
│   └── principles.md               # 投资原则（选股/开仓/组合/调仓/离场/风控/复盘）
├── data/
│   └── investment.db               # SQLite 数据库（自动创建）
└── .claude/
    └── commands/                   # slash commands（pm / researcher / risk）
```

---

## Coverage 系统

为每支持仓维护机构式投资论点，三维度结构：

```markdown
## Fundamental — 大方向
当前状态 / 支撑因子 / Base Scenario / Adverse Scenario / 监控指标

## Valuation — Risk/Return 评估
估值框架 / 多年 EPS 与 P/E 表 / Bear-Base-Bull 场景 / 胜率 / 估值锚点

## Technical — 资金流与市场结构
市场叙事 / 价格行为 / 分析师动态 / 资金流触发器

## 首要约束（Invalidation Conditions）
具体可观测、有时间边界的失效条件

## 头寸管理原则
目标权重 / 加仓条件 / 减仓条件 / 退出条件 / Time Horizon
```

**数据质量规范（强制）：**

- yfinance `eps_forward` 存在系统性年份偏移（返回 FY+2，非 FY+1），必须通过 StockAnalysis 交叉验证
- ADR（TSM 等）的 ps_ratio / ev_ebitda 因货币混用不可用，须手动计算
- 成本价（avg_cost）不入任何决策逻辑，仅用于 PnL 展示

---

## Position Metadata

每支持仓在 SQLite 中存储量化 metadata，供 `/pm:suggest` 读取：

```bash
# 读取所有标的 metadata
python app/tools/position_meta_tools.py read

# 写入 metadata（/researcher:update Step 5 调用）
python app/tools/position_meta_tools.py write NVDA \
  --target-bear 98 --target-base 198 --target-bull 308 \
  --prob-bear 0.15 --prob-base 0.40 --prob-bull 0.45 \
  --horizon-months 18 \
  --sector Technology --region US --cap-style mega \
  --growth-value growth \
  --risk-level high --ic-status CLEAR
```

期望 CAGR 由工具自动计算：`Σ prob_i × (target_i / current_price)^(12/horizon) - 1`

---

## 设计原则

| 原则 | 说明 |
|------|------|
| 确定性优先 | PnL / 权重 / 规则检查全部用 Python 计算，不靠 LLM |
| LLM 只做解释 | 语言生成、摘要、建议文字化才调用 Claude API |
| 人类决策 | 所有建议仅供参考，无自动执行 |
| 成本价不入 LLM | avg_cost 不传给 LLM prompt，避免沉没成本影响决策建议 |
| Thesis 硬性前提 | 所有持仓必须有完整 thesis 才允许加仓 |
| MVP 克制 | 美股 + ETF 先行，不做期权，不做自动交易 |

---

## 进度

详见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。

**当前状态（2026-03-24）：** Phase 1–5d 全部完成。10 个标的均有 Coverage thesis + Position metadata。`/pm:suggest` 可正常运行并存档。
