# Investment Agent

一个给会用 Agent 的个人投资者使用的 thesis-driven portfolio workflow skeleton。

它不替你交易，也不试图做一个通用 Agent 平台。它做的事情更朴素：把 portfolio state、research、review、decision 和 mistake memory 放进一个清晰、可协作、可回看的 repo 里，让你和 Agent 能围绕同一套规范长期工作。

## What this repo is

这是一个 tool-first、workflow-driven 的投资工作流项目。

它的核心组成是：
- 用 Python 维护确定性的持仓、现金、PnL、权重与规则检查
- 用 `coverage/` 维护每个标的的 thesis、版本和失效条件
- 用 `reviews/` 归档 daily review、组合建议、决策与执行记录
- 用 `postmortem` 记录 agent 自己的操作错误，避免重复犯错
- 用 `skills/investment-agent/` 和 `app/tools/*.py` 让任意 AI agent 协助研究与复盘

一句话讲：这是一个给 Agent 协作准备的投资工作流骨架，而不是一个“帮你自动炒股”的系统。

## What this repo is not

非目标很明确：
- 不是券商
- 不是自动交易系统
- 不自动下单
- 不提供前端 UI
- 不封装成通用 Agent framework
- 不要求绑定某个单一 LLM SDK 或某个单一数据供应商

## Who this repo is for

这个 repo 主要是给这样一群人准备的：
- 已经会用 Agent，愿意把 Agent 当作日常协作者
- 业余喜欢做投资，但还没有形成稳定规范 / 工作流
- 希望把持仓、thesis、review、decision 放到一个统一 repo 里
- 希望 Agent 帮自己做研究、检查、归档与复盘，而不是替自己做最终执行

如果你想找的是一个“点一下就自动完成投资”的黑盒系统，这个 repo 不适合你。

## How an Agent should operate in this repo

这个 README 虽然人也能读，但本质上就是给 Agent 和协作者的总入口。

建议 Agent 按这个顺序工作：

1. 先读 `README.md`
2. 再读 `skills/investment-agent/README.md`
3. 再读 `skills/investment-agent/project-context.md`
4. 再读对应 workflow 文档：`skills/investment-agent/workflows/*.md`
5. 执行时优先调用 `app/tools/*.py`
6. 只有人工原子操作、调试或最简单场景，才退回 `python run.py ...`
7. 不做自动执行，不跳过归档，不把主观叙事伪装成确定性计算结果

工作分层建议如下：
- `app/engines/`, `app/services/`, `app/repositories/`, `app/models/`
  - 业务逻辑和确定性计算层
- `app/tools/*.py`
  - Agent 的主接口层
- `python run.py ...`
  - 人工使用的薄 CLI
- `skills/investment-agent/workflows/*.md`
  - 高阶 workflow 文档层

原则上：
- 算术、状态、规则检查由 Python 完成
- 解释、总结、研究辅助交给 Agent
- 重要输出必须留痕到 repo

## 5-minute quickstart

目标不是先学会所有功能，而是先把 deterministic portfolio state 跑起来。

### 1) Install

```bash
pip install -r requirements.txt
cp .env.example .env
```

说明：
- 当前 `.env.example` 只给了 JQData / 聚宽示例变量
- 如果你暂时只跑美股 / 通用流程，也可以先不填 A 股凭证
- 如果你要使用当前仓库里的 A 股数据工具示例，再补 `JQ_USER` / `JQ_PASS`

### 2) Import or add positions

导入 CSV：

```bash
python run.py portfolio import portfolio.csv
```

CSV 头至少应包含：
- `symbol`
- `quantity`
- `avg_cost`
- 可选：`market`

也可以手动添加：

```bash
python run.py portfolio add AAPL 10 --cost 150
python run.py portfolio add 600519.SH 100 --cost 1680 --market CN_A
```

### 3) Inspect current state

```bash
python run.py portfolio summary
python run.py portfolio refresh
python run.py portfolio check
```

做到这里，你已经把这套系统最底层的 deterministic portfolio state 跑起来了。

下一步通常是二选一：
- 如果你只是先试用：继续看 `summary / refresh / check`
- 如果你准备正式使用：开始为核心持仓建立 `coverage/` 和 metadata

## The workflow at a glance

这个项目的重点不是“单个命令”，而是一条能长期运转的闭环。

### 1. Set up your portfolio state

先把组合状态维护起来：
- 导入或更新持仓
- 刷新价格
- 计算 PnL、权重、现金和 policy checks
- 让 `data/investment.db` 成为当前组合的确定性状态源

常见入口：

```bash
python run.py portfolio import portfolio.csv
python run.py portfolio summary
python run.py portfolio refresh
python run.py portfolio check
```

### 2. Build or update coverage

对于你真正要做 thesis-driven 判断的标的，应该建立 coverage。

这里的基本约定是：
- 每个标的一个目录：`coverage/{SYMBOL}/`
- 用版本文件保存 thesis，如 `v1_YYYY-MM-DD.md`
- `current.md` 只指向当前生效版本
- thesis 至少包含 Fundamental / Valuation / Technical / Invalidation Conditions / 头寸管理原则 / 覆盖历史

相关 workflow：
- `skills/investment-agent/workflows/researcher-initiate.md`
- `skills/investment-agent/workflows/researcher-update.md`
- `skills/investment-agent/workflows/researcher-analyze.md`
- `skills/investment-agent/workflows/researcher-note.md`
- `skills/investment-agent/workflows/researcher-status.md`

一个重要约束是：
- 没有 coverage thesis 的标的，不应伪装成做了 thesis-driven 的加仓建议

### 3. Run the daily loop

日常循环通常是：
- refresh 组合状态
- record PnL snapshot
- 读取 position metadata
- 跑 policy check
- 对照 coverage thesis 看当前状态
- 产出 daily review 或组合建议

相关 workflow：
- `skills/investment-agent/workflows/daily-review.md`
- `skills/investment-agent/workflows/pm-suggest.md`
- `skills/investment-agent/workflows/risk-ic.md`

推荐工具：
- `app/tools/portfolio_tools.py`
- `app/tools/pnl_tools.py`
- `app/tools/position_meta_tools.py`
- `app/tools/policy_tools.py`

### 4. Make a decision before trading

在真正执行调仓前，先形成 decision，而不是边想边改仓位。

这一步通常会：
- 读取 coverage 和最新 suggest
- 记录方向、数量、参考价、资金来源、理由、替代方案
- 生成 decision 文件
- 追加到 `reviews/REVIEWS_LOG.md`

相关 workflow：
- `skills/investment-agent/workflows/trader-decide.md`

重点：
- decision 文件是计划与理由的归档
- 它不是成交回执

### 5. Record execution after trading

成交后，再更新执行结果，而不是把计划和结果混在一起。

这一步通常会：
- 更新 decision 文件状态
- 更新 portfolio DB 和现金余额
- refresh 最新价格
- 记录一条执行后的 PnL snapshot
- 追加执行记录到 review log

相关 workflow：
- `skills/investment-agent/workflows/trader-record.md`

### 6. Capture agent mistakes with postmortem

这个项目不仅记录投资判断，也记录 agent 的操作错误。

适合进入 postmortem 的内容：
- 数据误读
- 逻辑错误
- 漏步骤
- 格式错误
- 本可以避免的 workflow 违规

不适合进入 postmortem 的内容：
- 普通投资观点本身
- coverage thesis 的替代版本
- review archive 的替代品

相关 workflow：
- `skills/investment-agent/workflows/postmortem-create.md`
- `skills/investment-agent/workflows/postmortem-list.md`
- `skills/investment-agent/workflows/postmortem-check.md`

## Data sources and provider strategy

数据源是接入层，不应该被写死成这个项目的定义。

当前仓库里的默认示例是：
- US / global 价格与部分市场数据：项目当前实现里会用到 yfinance 等通用来源
- CN_A 基本面 / 市场数据：当前 workflow 示例偏向 `app/tools/cn_market_data_tools.py`
- `.env.example` 当前提供的是 JQData / 聚宽示例变量：`JQ_USER` / `JQ_PASS`

但这不代表：
- 聚宽是唯一正确的数据源
- A 股必须绑定某一个 provider 才能使用这套 workflow
- provider 输出可以不经验证直接写进 thesis

更准确的理解应该是：
- workflow 是长期稳定的
- provider 是可以替换的
- 工具层是接入点
- 敏感字段必须交叉验证

### 一个简单的 provider 视角

| 用途 | 当前仓库中的默认示例 | 是否可替换 | 备注 |
| --- | --- | --- | --- |
| Portfolio state / policy checks | Python 本地计算 | 否，计算逻辑应保持确定性 | 这是工作流底座，不应外包给 LLM |
| US / global 市场数据 | 当前实现中的通用 provider（如 yfinance） | 是 | 适合快速接入，但某些字段要谨慎 |
| CN_A 基本面 / 市场数据 | `app/tools/cn_market_data_tools.py` + JQData 示例 | 是 | README 不应把 JQData 写成唯一依赖 |
| Thesis 中的关键估值字段验证 | 第二数据源 / 人工交叉验证 | 应当保留 | EPS、Forward P/E、ADR 指标尤其要谨慎 |

### 当前已知的数据质量约束

1. `eps_forward` 可能年份错位
- yfinance 的 `eps_forward` 可能返回 FY+2E 而不是 FY+1E
- 写入 thesis 前必须用第二数据源交叉验证
- EPS / P-E 数字最好标明来源与财年

2. ADR 的部分比率不可直接照搬
- 如 TSM 等 ADR 的 `ps_ratio`、`ev_ebitda` 可能因货币混用而失真
- 这类指标应手算、谨慎使用，或干脆省略

3. A 股不要直接把 yfinance 当主基本面源
- 如果沿用当前 repo 的默认示例，应优先看 `app/tools/cn_market_data_tools.py`
- 但底层 provider 仍然可以根据你的环境替换

## What you should customize

这套 repo 不是要求你接受作者的全部默认偏好。相反，它有一部分是故意留给你定制的。

### 最值得优先改的文件

| 路径 | 作用 | 默认还是用户自有 | 何时该改 | 影响 |
| --- | --- | --- | --- | --- |
| `config/principles.md` | 你的投资原则文档 | 默认模板，应该逐步变成你的 | 一开始就可以改 | 影响 PM suggest、定性判断边界、研究与决策风格 |
| `config/profile.json` | 风险偏好、仓位上限、现金下限、禁投标的等结构化配置 | 默认配置 | 你准备正式使用时就该改 | 影响 policy checks 和部分 profile-driven logic |
| `coverage/THESIS_TEMPLATE.md` | coverage thesis 模板 | 默认模板 | 你想调整分析框架时再改 | 应尽量保持结构稳定，避免破坏 workflow 一致性 |
| `app/prompts/daily_review.md` | daily review 输出结构 | 默认模板 | 你想调整输出风格时改 | 应保留事实约束，不要鼓励编造数据 |
| `app/prompts/asset_analysis.md` | 单标的分析 prompt | 默认模板 | 你想改变分析表达方式时改 | 影响 agent 的分析口径 |
| `skills/investment-agent/workflows/*.md` | Agent workflow 规范 | 默认协作协议 | 你有更成熟的协作方式时改 | 影响 Agent 的执行顺序和留痕方式 |
| `.env` | 数据源 / 外部服务凭证 | 用户自有 | 接入数据源时必改 | 当前示例含 JQData / 聚宽变量，但不限定必须用它 |

### 两个特别重要的定制点

#### `config/principles.md`

这是默认化的投资原则模板，不是不可碰的“系统真理”。

你应该把它逐步改成：
- 你认可的选股原则
- 你的组合原则
- 你的调仓 / 离场原则
- 你的风控底线
- 你的复盘方法

也就是说，这个 repo 不是在强迫你接受作者的投资哲学，而是在给你一个可继承、可修改的默认起点。

#### 数据源配置

当前仓库只是提供了一个能跑通的默认示例，不是在宣称“聚宽 = 唯一标准答案”。

如果你有更适合自己的 A 股数据源：
- 可以替换 provider
- 可以保留 workflow
- 可以保留 deterministic 计算和 archive 机制
- 只要你仍然满足同样的数据需求与质量要求

## Repo map

这个仓库更适合按“功能层”理解，而不是只看目录树。

### 1. Runtime entry
- `run.py`
  - 统一入口，适合人工直接运行 CLI

### 2. Core logic
- `app/engines/`
- `app/services/`
- `app/repositories/`
- `app/models/`
  
这部分负责：
- 组合状态计算
- 市场数据接入
- 持久化
- recommendation / policy / thesis 相关逻辑

### 3. Human CLI
- `app/cli/`
- `python run.py ...`

这是面向人工的薄 CLI，适合：
- import
- add / remove
- summary
- refresh
- check
- 简单分析与调试

### 4. Agent tool layer
- `app/tools/*.py`

这是 Agent 的主要操作面。

当前已看到的工具包括：
- `app/tools/portfolio_tools.py`
- `app/tools/pnl_tools.py`
- `app/tools/policy_tools.py`
- `app/tools/position_meta_tools.py`
- `app/tools/cn_market_data_tools.py`
- `app/tools/postmortem_tools.py`

### 5. Workflow docs
- `skills/investment-agent/README.md`
- `skills/investment-agent/project-context.md`
- `skills/investment-agent/workflows/*.md`

这里定义的是高阶协作方式，而不是具体实现细节。

### 6. Research and archive
- `coverage/`
- `reviews/`

这里保存的是：
- thesis
- review
- suggest
- decision
- 执行记录
- 统一索引

### 7. User-owned config
- `config/principles.md`
- `config/profile.json`
- `.env`

这些文件不是 repo 的“神圣常量”，而是你最应该逐步定制的部分。

## Analysis and decision principles

无论你底层接什么 provider、用什么 Agent，下面这些约束最好保持稳定：

- 确定性优先：PnL / 权重 / policy checks / CAGR 等数值计算由 Python 完成，不让 LLM 做算术
- `avg_cost` 不进入建议逻辑：它只用于展示和 P&L，不应支配加仓 / 减仓 / 离场判断
- Thesis first：没有 thesis，就不要伪装成做了 thesis-driven 的建议
- Invalidation first：IC 的优先级高于叙事、情绪和“再等等看”
- Data quality first：敏感估值字段要交叉验证，不把 provider 输出当作绝对真相
- Agent assists, human decides / executes：Agent 负责解释、组织、提醒、留痕，不负责替你自动执行
- Archive important things：review、decision、thesis 更新、postmortem 都应该留痕

更多上下文见：
- `skills/investment-agent/project-context.md`
- `coverage/THESIS_TEMPLATE.md`

## Local data and privacy

这个仓库的设计目标，是让代码和 workflow 可以公开，而真实运行数据尽量只留本地。

默认建议本地保留的内容包括：
- `data/` 运行时数据库
- `reviews/` 下的真实 daily / suggest / decision 历史
- 大部分真实 `coverage/{SYMBOL}/` thesis 文件
- 本地 benchmark 或评估输出

一个健康的协作方式通常是：
- 把 workflow、模板、工具代码放在可共享 repo
- 把真实组合状态、真实研究历史、隐私数据留在本地并 ignore

## Read next

如果你准备真正开始使用，推荐继续读：

1. `skills/investment-agent/README.md`
   - 理解 workflow 层的整体设计
2. `skills/investment-agent/project-context.md`
   - 理解数据层、核心约束、数据质量坑
3. `skills/investment-agent/workflows/*.md`
   - 按场景选择具体 workflow

优先建议看这些 workflow：
- `skills/investment-agent/workflows/daily-review.md`
- `skills/investment-agent/workflows/pm-suggest.md`
- `skills/investment-agent/workflows/researcher-initiate.md`
- `skills/investment-agent/workflows/researcher-update.md`
- `skills/investment-agent/workflows/risk-ic.md`
- `skills/investment-agent/workflows/trader-decide.md`
- `skills/investment-agent/workflows/trader-record.md`
- `skills/investment-agent/workflows/postmortem-create.md`
- `skills/investment-agent/workflows/postmortem-check.md`

## Current status

这个项目已经可以作为一个开源的个人投资工作流项目来体验和使用，但它仍然会继续演进。

当前更重要的不是某个固定实现细节，而是这几件事：
- workflow、tooling、archive 和 thesis 结构已经基本成型
- 它适合拿来体验 Agent-assisted investing workflow 是怎么组织起来的
- 你可以直接按自己的习惯修改原则、数据源、prompt 和 workflow 文档

如果你对这类方向感兴趣，非常欢迎：
- 直接体验
- fork 成你自己的版本
- 提 issue 提建议
- 提交 PR 一起把这套 workflow 打磨得更清晰、更好用

如果只能选一个，我最欢迎的是 fork 和贡献。

## License

这个仓库采用双协议、默认非商用的授权方式：

- 软件 / 代码：`PolyForm Noncommercial 1.0.0`
- 文档 / README / workflow / prompts / 模板等内容：`CC BY-NC 4.0`

对应文件：
- `LICENSE`：代码协议全文
- `LICENSE-docs`：文档协议全文
- `LICENSES.md`：本仓库的适用范围说明

一句话理解：
- 欢迎你出于学习、研究、个人使用、非商用协作来体验、fork、修改和贡献
- 默认不授权商用
- 如果某个子目录或文件有更具体的协议说明，则以更具体的说明为准
