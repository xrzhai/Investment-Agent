# Investment Agent — 项目进度与架构

> 最后更新：2026-03-25（Mistake Memory 模块上线）
> 开发者：个人独立开发
> 定位：个人投资 Copilot，自用第一，Claude Code 主接口 + CLI 辅助

---

## 核心设计原则

| 原则 | 说明 |
|------|------|
| 确定性优先 | PnL / 权重 / 规则检查 全部用 Python 计算，不靠 LLM |
| LLM 只做解释 | 语言生成、摘要、建议文字化才调用 Claude API |
| 人类决策 | 所有建议仅供参考，无自动执行 |
| MVP 克制 | 美股 + ETF 先行，不做期权、不做自动交易 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.12（conda `work` 环境） |
| CLI | Typer + Rich |
| Domain Models | Pydantic v2 |
| 数据库 | SQLite + SQLModel |
| 市场数据 | yfinance（免费，美股/ETF）+ JQData（A 股） |
| 可视化 | plotext（终端 ASCII 折线图） |
| LLM | Anthropic Claude API（claude-sonnet-4-6） |
| 运行方式 | `python run.py <命令>` |

---

## 项目结构

```
investment-agent/
│
├── run.py                          # 入口文件，直接 python run.py --help
├── portfolio.csv                   # 持仓数据（CSV 导入源）
│
├── app/
│   ├── main.py                     # 注册所有 CLI 命令组
│   │
│   ├── cli/                        # 用户交互层（命令定义）
│   │   ├── portfolio.py            # portfolio add/import/summary/snapshot/check/refresh
│   │   ├── profile.py              # profile init/show/update
│   │   ├── analyze.py              # analyze portfolio/asset, suggest
│   │   ├── journal.py              # journal add/list/review/research
│   │   └── daily.py                # daily run（全流程串联）
│   │
│   ├── models/
│   │   ├── domain.py               # Pydantic domain models（纯数据结构）
│   │   └── db.py                   # SQLModel 表定义 + DB 初始化
│   │
│   ├── engines/                    # 业务逻辑层（无 I/O，可单独测试）
│   │   ├── portfolio_engine.py     # 计算 PnL / 权重 / 集中度
│   │   ├── policy_engine.py        # 规则检查 → PolicyResult
│   │   └── recommendation_engine.py # 草稿生成 + LLM 文字化
│   │
│   ├── services/                   # 外部集成层
│   │   ├── market_data.py          # yfinance：价格 / 新闻
│   │   ├── llm_client.py           # Claude API 封装
│   │   ├── profile_service.py      # 投资者配置读写（JSON）
│   │   └── coverage_service.py     # Coverage thesis 读取（current.md 指针）
│   │
│   ├── repositories/               # 数据持久化层（SQLite CRUD）
│   │   ├── portfolio_repo.py        # 持仓 / 快照 / position metadata
│   │   └── journal_repo.py         # 日志 / 推荐记录 / research notes
│   │
│   ├── tools/                      # Claude Code 调用层（输出 JSON）
│   │   ├── portfolio_tools.py      # python app/tools/portfolio_tools.py [--refresh]
│   │   ├── policy_tools.py         # python app/tools/policy_tools.py
│   │   ├── position_meta_tools.py  # python app/tools/position_meta_tools.py read/write
│   │   ├── pnl_tools.py            # python app/tools/pnl_tools.py --record/--cashflow/--curve
│   │   └── postmortem_tools.py     # python app/tools/postmortem_tools.py --create/--approve/--recall/--list
│   │
│   └── prompts/                    # LLM prompt 模板
│       ├── daily_review.md         # 日检报告结构
│       └── asset_analysis.md       # 单资产分析结构
│
├── .claude/
│   └── commands/                   # Slash commands（Claude Code 工作流）
│       ├── pm/                     # 组合管理角色
│       │   ├── daily.md            # /pm:daily — 完整日检（自动打 P&L 快照）
│       │   ├── suggest.md          # /pm:suggest — 可操作建议（含 Step 7 存档，自动打快照）
│       │   ├── snapshot.md         # /pm:snapshot — 快速持仓快照
│       │   ├── curve.md            # /pm:curve — P&L 曲线展示（ASCII 折线图）
│       │   └── cashflow.md         # /pm:cashflow — 记录入出金事件
│       ├── researcher/             # 研究员角色（Coverage 工作流）
│       │   ├── initiate.md         # /researcher:initiate — 发起覆盖
│       │   ├── update.md           # /researcher:update — 更新覆盖
│       │   ├── analyze.md          # /researcher:analyze — 单持仓深度分析
│       │   ├── note.md             # /researcher:note — 记录研究笔记
│       │   └── status.md           # /researcher:status — 覆盖状态总览
│       └── risk/                   # 风险角色
│           ├── check.md            # /risk:check — 规则检查
│           └── ic.md               # /risk:ic — IC 扫描
│
├── coverage/                       # 投资论点（每支股票一个子目录）
│   ├── COVERAGE_WORKFLOW.md        # 工作流文档（核心原则、流程、质量控制）
│   ├── COVERAGE_LOG.md             # 所有持仓覆盖状态一览（13 个标的）
│   ├── THESIS_TEMPLATE.md          # 空白模板（三维度结构）
│   ├── NVDA/  META/  TSM/  GOOGL/  # 已覆盖（各含 v1..vN + current.md）
│   ├── ALLW/  BMNR/  MSFT/  NFLX/
│   ├── PDD/   BTC-USD/
│   ├── 000975.SZ/  601899.SH/  600036.SH/  # A 股（JQData + WebSearch）
│   └── {SYMBOL}/                   # vN_YYYY-MM-DD.md + current.md（指针）
│
├── reviews/                        # 组合级分析存档（按事件类型分，与 coverage 平行）
│   ├── REVIEWS_LOG.md              # 所有运行记录总览索引
│   ├── suggest/                    # /pm:suggest 输出存档
│   │   └── YYYY-MM-DD_suggest.md  # 每次运行后自动写入
│   └── daily/                      # /pm:daily 输出（预留）
│
├── scripts/                        # 一次性工具脚本
│   └── batch_write_meta.py         # 批量写入 9 个标的 position metadata
│
├── data/
│   └── investment.db               # SQLite 数据库（自动创建）
│
├── config/
│   ├── profile.json                # 投资者配置文件
│   └── principles.md               # 投资原则（选股/开仓/组合/调仓/离场/风控/复盘）
│
├── mine investment policy/         # 投资哲学参考文档（只读）
│
└── tests/                          # 测试目录（待填充）
```

---

## Domain Models（核心数据结构）

```
Asset            symbol / name / asset_type / sector / market
Position         symbol / quantity / avg_cost / current_price
                 market_value / unrealized_pnl / weight
PositionRow      (DB) + target_bear/base/bull / prob_bear/base/bull
                 expected_cagr / time_horizon_months
                 sector / region / cap_style / growth_value
                 theme_tags (JSON) / risk_level / ic_status / meta_updated_at
PortfolioSnapshot  date / total_value / positions[] / daily_return / drawdown
InvestorProfile  style / time_horizon / risk_tolerance
                 max_position_weight / max_drawdown_tolerance
                 forbidden_symbols[]
Event            type / timestamp / related_symbols[] / title / importance
RecommendationDraft  scope / trigger_type / suggested_action
                     rationale[] / evidence[] / risk_notes[] / confidence
Recommendation   scope / action / reason / evidence[] / risk_notes[]
JournalEntry     scope / thesis / user_note / agent_note / linked_rec_ids[]
```

---

## 完整 CLI 命令列表

```bash
# 持仓管理
python run.py portfolio add <SYMBOL> <QTY> --cost <PRICE>
python run.py portfolio remove <SYMBOL>
python run.py portfolio import <file.csv>       # CSV: symbol,quantity,avg_cost
python run.py portfolio summary                 # 持仓表格
python run.py portfolio snapshot                # 保存当日快照
python run.py portfolio check                   # 运行 policy 规则检查
python run.py portfolio refresh                 # 拉取最新价格（yfinance）

# 投资者配置
python run.py profile init                      # 交互式初始化
python run.py profile show
python run.py profile update <field> <value>

# 分析与建议（需要 ANTHROPIC_API_KEY）
python run.py analyze portfolio                 # LLM 解释组合状态
python run.py analyze asset <SYMBOL>            # LLM 解释个股新闻
python run.py analyze suggest                   # 生成可解释操作建议

# 投资日志
python run.py journal add <SYMBOL> --thesis "..." --note "..."
python run.py journal list [SYMBOL]
python run.py journal review <SYMBOL>

# 每日全流程
python run.py daily run                         # refresh → check → analyze → suggest

# Position Metadata（Claude Code 调用层）
python app/tools/portfolio_tools.py --refresh   # JSON 输出持仓状态
python app/tools/policy_tools.py                # JSON 输出 policy 检查
python app/tools/position_meta_tools.py read [SYMBOL]       # 读取 metadata
python app/tools/position_meta_tools.py write SYMBOL [args] # 写入 metadata
```

---

## 开发进度

### Phase 1 — 项目骨架 ✅ 完成

- [x] 项目目录结构初始化
- [x] 依赖安装：typer / pydantic / sqlmodel / yfinance / anthropic / rich
- [x] Domain Models 定义（`app/models/domain.py`）
- [x] SQLite 数据库初始化（`app/models/db.py`）
- [x] CLI 骨架搭建，所有命令组注册可用（`python run.py --help`）
- [x] Portfolio Engine：PnL / 权重计算
- [x] Policy Engine：集中度 / 禁止标的规则检查
- [x] Recommendation Engine：结构化草稿 + LLM 文字化框架
- [x] yfinance 市场数据服务封装
- [x] Claude API 客户端封装
- [x] 投资者配置（JSON 读写）
- [x] 持仓 / 快照 / 日志 Repository 层

---

### Phase 2 — Claude Code 接口层 + 市场数据 ✅ 完成

- [x] `app/tools/portfolio_tools.py`：独立 JSON 输出脚本，支持 `--refresh` 实时拉价
- [x] `app/tools/policy_tools.py`：独立 JSON 输出脚本，输出 policy 检查结果
- [x] `app/prompts/`：日检 / 资产分析 prompt 模板
- [x] `.claude/commands/` slash commands（pm / researcher / risk 三组角色）
- [x] `portfolio refresh` 端到端验证（yfinance → 更新价格 → 权重检测正常）
- [x] CSV 导入端到端测试（`portfolio.csv` 11 支持仓导入成功）
- [ ] 补充回撤计算（需要多日快照历史）

---

### Phase 3 — LLM 层端到端 ✅ 完成

**注：通过 Claude Code 订阅调用，无需单独设置 `ANTHROPIC_API_KEY`**

- [x] 测试 `analyze portfolio`（LLM 解释组合状态）
- [x] 测试 `analyze suggest`（生成建议，NVDA/META 超重触发 CONSIDER TRIM）
- [x] 测试 `analyze asset NVDA`（新闻解释，修复了 yfinance news 结构变更）
- [x] 验证建议自动写入 DB（recommendations 表，与用户手动 journal 分开）
- [x] 确认 LLM 建议不引用成本价（prompt 层不传 avg_cost；asset_analysis.md 文档加注）

---

### Phase 4 — Daily Run 完整流程 ✅ 完成

- [x] 端到端测试 `daily run`（全链路：refresh → check → analyze → suggest）
- [ ] 日报格式优化（可选）
- [ ] `journal review` 查看历史建议（可选）

---

### Phase 5 — Coverage 系统 ✅ 完成

专业机构式投资论点管理，为每支持仓维护结构化覆盖文档，集成到 LLM 分析流程。

**已完成：**

- [x] 创建 `coverage/` 目录结构（每个 ticker 一个子目录）
- [x] Thesis 文档格式规范（`coverage/THESIS_TEMPLATE.md`，三维度：Fundamental / Valuation / Technical + IC + 头寸管理原则）
- [x] `current.md` 指针机制（一行指向当前生效版本文件名）
- [x] `coverage/COVERAGE_LOG.md` 总览（10 个标的覆盖状态一览）
- [x] `coverage/COVERAGE_WORKFLOW.md` — 完整工作流文档（核心原则、发起/更新流程、Thesis Checklist、数据质量规范）
- [x] Claude Code Researcher Skills（`.claude/commands/researcher/`）完整集成
- [x] **13 个标的全部建立初始覆盖（含覆盖历史和 IC）：**

  | Symbol | 最新版本 | 完成日期 | 数据源 |
  | --- | --- | --- | --- |
  | NVDA | v4（yfinance 年份修正） | 2026-03-17 | yfinance |
  | META | v2（yfinance 年份修正） | 2026-03-17 | yfinance |
  | TSM | v2（yfinance 年份修正） | 2026-03-17 | yfinance |
  | GOOGL | v2（yfinance 年份修正） | 2026-03-17 | yfinance |
  | ALLW | v1 | 2026-03-18 | yfinance |
  | BMNR | v1 | 2026-03-20 | yfinance |
  | MSFT | v1 | 2026-03-20 | yfinance |
  | NFLX | v1 | 2026-03-20 | yfinance |
  | PDD | v1 | 2026-03-20 | yfinance |
  | BTC-USD | v1 | 2026-03-24 | yfinance |
  | 000975.SZ | v4（FY2025 年报 + 黄金/白银情景矩阵） | 2026-03-24 | JQData + WebSearch |
  | 601899.SH | v3（铜价情景系统化 + 2D EPS 敏感性） | 2026-03-24 | JQData + WebSearch |
  | 600036.SH | v1 | 2026-03-24 | JQData + WebSearch |

- [x] `config/principles.md` 完整填写（7 个模块：选股/开仓/组合/调仓/离场/风控/复盘）

**未实现（Python App 层，已判断优先级低）：**

- [ ] CLI 命令：`coverage initiate / update / list`（目前通过 Claude Code skills 操作，已满足需求）
- [ ] 集成到 `analyze asset`：读取 thesis → 判断新闻是否影响论点（Pythonic 路径）
- [ ] 集成到 `analyze suggest`：有 coverage 时注入 thesis context；无则降级提示

---

### Phase 5b — Position Metadata 系统 ✅ 完成（2026-03-24）

为每支持仓在 DB 中存储量化 metadata，支撑 pm:suggest 的 CAGR 计算和主题聚类。

- [x] `app/tools/position_meta_tools.py` — CLI 工具（write/read），支持：
  - Bear / Base / Bull 目标价 + 概率
  - 期望 CAGR（基于当前价、目标价、持仓期限的年化加权回报）
  - sector / region / cap_style / growth_value
  - theme_tags（JSON 数组，支持中文）
  - risk_level / ic_status / meta_updated_at
- [x] Windows 编码问题处理（sys.argv 重新编码，stdout reconfigure）
- [x] `scripts/batch_write_meta.py` — 一次性批量写入脚本（绕过 CLI 编码问题）
- [x] 所有 10 个持仓 metadata 写入 DB 并验证

---

### Phase 5c — pm:suggest 完整闭环 ✅ 完成（2026-03-24）

基于 Position Metadata 和 Coverage Thesis 的可操作组合建议系统。

- [x] `/pm:suggest` skill 完整实现（6 Steps）：
  - Step 0：Coverage gate + metadata 时效检查
  - Step 1：从 portfolio_tools + position_meta_tools 构建工作表
  - Step 2：policy check
  - Step 3：加载 config/principles.md 作为定性框架
  - Step 4：组合诊断（主题敞口语义聚类 / 地区 / 风格 / IC 汇总）
  - Step 5：个股建议（按 IC → Policy → 超重 → 机会 → Hold 优先级）
  - Step 6：摘要（Priority Action / Risk Alerts / Best Opportunity）
- [x] **Step 7 — Archive**：自动将输出存入 `reviews/suggest/YYYY-MM-DD_suggest.md`
- [x] 首次运行验证完成（2026-03-24，组合总值 $88,716）

---

### Phase 5d — Reviews 存档系统 ✅ 完成（2026-03-24）

机构式组合级分析存档，与 coverage/（标的级 thesis）平行，按事件类型组织。

- [x] `reviews/` 顶层目录（与 coverage/ 平行）
- [x] `reviews/REVIEWS_LOG.md` — 所有运行记录总览索引
- [x] `reviews/suggest/` — pm:suggest 输出存档目录
- [x] `reviews/daily/` — pm:daily 输出预留目录
- [x] 存档文档标准格式（Frontmatter / Executive Summary / 组合诊断 / 个股建议表 / 数据快照 / 执行跟踪）
- [x] 首份存档：`reviews/suggest/2026-03-24_suggest.md`

---

### Phase 5e — P&L 曲线记录系统 ✅ 完成（2026-03-24）

资金曲线与时间加权收益率（TWR）记录，支持入出金调整，终端 ASCII 折线图展示。

- [x] `app/models/db.py` — 新增 `CashflowEventRow` 表；`SnapshotRow` 加 `notes` 列；`init_db()` 自动迁移
- [x] `app/repositories/portfolio_repo.py` — 新增 `upsert_pnl_snapshot` / `save_cashflow` / `list_cashflows` / `list_snapshots_asc`
- [x] `app/tools/pnl_tools.py` — 独立工具脚本：
  - `--record [--notes TEXT]`：记录当日组合资金快照（upsert，同一天覆盖）
  - `--cashflow AMOUNT [--desc TEXT]`：记录入出金事件，自动在事件前打快照保证 TWR 精度
  - `--curve [--days N]`：用 plotext 在终端输出双图（资金曲线 + TWR 累计收益率）
- [x] `/pm:daily` / `/pm:suggest` — Step 1 / Step 0 后自动调用 `pnl_tools.py --record`
- [x] `.claude/commands/pm/curve.md` — `/pm:curve` 命令
- [x] `.claude/commands/pm/cashflow.md` — `/pm:cashflow` 命令
- [x] `requirements.txt` — 追加 `plotext`
- [x] 历史记录清空，以 2026-03-24（$98,430 USD，A 股已合并）为 TWR 基准起点

**TWR 算法：** 区间加权乘积法。每个子区间回报 = (期末 - 期间现金流) / 期初，所有子区间连乘后减 1 得累计 TWR。

---

### Phase 5f — Mistake Memory 模块 ✅ 完成（2026-03-25）

Agent 操作错误的结构化记忆系统。记录 Agent 自身的操作失误（数据误读、计算偏差、逻辑矛盾、漏步骤、格式错误），在后续任务中召回并自查，避免重复犯错。

- [x] `app/models/db.py` — 新增 `MistakeMemoryRow` 表（5 类错误 + 4 核心字段 + 状态流转）；`init_db()` 自动迁移
- [x] `app/tools/postmortem_tools.py` — 独立工具脚本：
  - `--create`：从 stdin 读取 JSON，写入 draft 条目
  - `--approve <id>`：draft → active（激活后才参与召回）
  - `--retire <id>`：归档（不再召回）
  - `--recall --task <scope> [--symbol <symbol>]`：结构化匹配，按 severity + confidence 排序，返回 top-5
  - `--list [--status ...]`：列出全量条目
- [x] `.claude/commands/postmortem/create.md` — `/postmortem:create`：引导用户描述错误，LLM 生成结构化草稿，写入 DB
- [x] `.claude/commands/postmortem/list.md` — `/postmortem:list`：按 draft/active/retired 分组展示，支持 approve/retire 操作
- [x] `.claude/commands/postmortem/check.md` — `/postmortem:check`：召回相关历史教训，逐条核查当前输出，标记 ✅/❌/⚪，自动修正 ❌ 项
- [x] 首条记录写入验证：yfinance eps_forward 年份偏移问题（severity=high，status=active）

**错误类型分类：**

| mistake_type | 含义 |
|---|---|
| `data` | 数据读取/解析错误（字段误读、单位混用） |
| `calculation` | 计算公式错误（CAGR 月/年混用、权重分母错误） |
| `logic` | 逻辑矛盾（建议与 IC 状态/principles 冲突） |
| `omission` | 漏步骤（未加载 coverage/principles 就出结论） |
| `format` | 输出格式错误（表格错位、markdown 嵌套破坏） |

---

### Phase 6 — 事件层 🔲 待开始（可选，按需）

- [ ] 手动事件录入 CLI（`event add`）
- [ ] 事件与持仓标的关联
- [ ] 事件纳入 `analyze asset` 分析

---

### Phase 7 — 定时自动化 🔲 待开始（可选，后期）

- [ ] APScheduler 定时触发 `daily run`
- [ ] 回撤 / 超重阈值触发告警
- [ ] 可选：简单 Web UI（FastAPI）

---

## 数据流：一次 /pm:suggest 的完整路径

```text
/pm:suggest
    |
    v
[0] Coverage gate
    ls coverage/{SYMBOL}/current.md  ← 检查所有持仓是否有 thesis
    position_meta_tools.py read      ← 检查 metadata 是否新鲜（≤30天）
        |
        v
[1] Load state
    portfolio_tools.py --refresh     ← 实时价格 + 权重
    position_meta_tools.py read      ← CAGR + 场景目标价 + theme_tags
        |
        v
[2] Policy check
    policy_tools.py                  ← 规则违规（硬约束）
        |
        v
[3] Load principles
    config/principles.md             ← 投资原则（定性框架）
        |
        v
[4] Portfolio diagnosis
    主题敞口（语义聚类） → 地区敞口 → 风格快照 → IC 汇总
        |
        v
[5] Per-stock recommendations
    coverage/{SYMBOL}/current.md     ← 读取头寸管理原则（目标权重/加减仓条件）
    优先级：IC triggered > Policy > 超重 > CAGR机会 > Hold
        |
        v
[6] Summary
    Priority Action / Risk Alerts / Best Opportunity
        |
        v
[7] Archive
    reviews/suggest/YYYY-MM-DD_suggest.md  ← 存档（含数据快照 + 执行跟踪）
    reviews/REVIEWS_LOG.md                 ← 追加索引行
```

---

## 快速开始

```bash
# 1. 进入项目目录
cd "g:/我的云端硬盘/03_Work/Projects/Investment-Agent"

# 2. 检查持仓状态
python app/tools/portfolio_tools.py --refresh

# 3. 检查 metadata 完整性
python app/tools/position_meta_tools.py read

# 4. 在 Claude Code 中运行完整工作流
/pm:suggest        # 组合诊断 + 个股建议（含存档）
/pm:daily          # 完整日检
/researcher:status # 覆盖状态总览
/risk:ic           # IC 扫描
```

---

## 已知问题 / 待优化

| 问题 | 优先级 | 说明 |
| --- | --- | --- |
| 回撤计算简化 | 中 | 目前只比较昨日快照，未计算历史峰值回撤 |
| `portfolio check` 无价格时不检查权重 | 低 | 需先 refresh 才有权重数据 |
| 无单元测试 | 中 | engines/ 层适合优先补测试 |
| yfinance eps_forward 年份错位 | 已记录 | 固定为 FY+2（非 FY+1），见 memory/feedback_yfinance_data_issues.md；所有 thesis 已交叉验证 |
| TSM ADR ps_ratio / ev_ebitda 货币混用 | 已记录 | yfinance 不可用，须手动计算；已在 TSM thesis 中标注 |
| Windows CLI 编码（中文 theme_tags） | 已绕过 | 使用 Python 脚本直接写入 DB，不经 Git Bash 命令行传参 |
