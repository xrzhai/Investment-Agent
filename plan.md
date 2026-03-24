# A 股全链路接入方案（Markdown 草稿）

## 文档信息
- 建议文件名：`docs/plans/2026-03-24_a-share-integration-plan.md`
- 目的：作为 A 股接入的实施计划文档，供逐条审阅、修改、再执行
- 当前决策：
  - 接入范围：A 股全链路
  - 数据源策略：混合源
  - 组合基准货币：`USD`

---

## 1. 背景与现状

根据当前项目文档与既有工作流，项目已经具备以下能力：

- `portfolio / profile / analyze / daily` 主链路已完成
- `.claude/commands/pm/*` 与 `.claude/commands/researcher/*` 工作流已存在
- `coverage/` thesis 机制已存在，并已接入建议与分析链路
- 当前市场数据主路径默认围绕 `yfinance`
- 当前组合模型、命令文档、symbol 约定仍明显偏美股

这意味着 A 股接入不应继续在现有 `yfinance` 逻辑上做局部补丁，而应把以下能力升级为正式抽象层：

- 市场类型
- 证券代码规范
- 数据源路由
- 汇率与多币种汇总
- thesis / suggest / daily 对不同市场的适配

---

## 2. 目标

本轮目标是让系统同时支持美股与 A 股，并在以下链路中可用：

- 持仓导入
- 实时刷新
- 组合汇总
- 规则检查
- 单标的分析
- 建议生成
- coverage / thesis 管理
- researcher / pm 命令工作流

本轮不做：

- 自动下单
- 可转债、期权、期货、场外基金
- 港股支持
- A 股交易规则深度建模（如 T+1、涨跌停、最小申报单位的执行约束）

---

## 3. 总体方案

### 3.1 核心设计原则

- 不破坏现有美股路径
- 统一市场抽象，而不是为 A 股写特殊分支脚本
- 组合层所有规则检查统一在基准货币上完成
- thesis 模板结构保持不变，仅按市场切换数据来源与数据质量规则
- 行情、财务、市场上下文分层获取，避免单一数据源承担所有职责

### 3.2 数据源策略

采用混合源策略：

- 美股：继续使用 `yfinance`
- A 股核心主数据：使用 `Tushare Pro`
- A 股补充与回退：使用 `AkShare`

A 股中各类数据的优先级如下：

- 股票基础信息：Tushare
- 日线 / 复权 / 历史行情：Tushare
- 财务数据 / 估值指标：Tushare
- 交易日历：Tushare
- 汇率：Tushare
- 题材 / 资金流 / 市场补充信息：AkShare
- 报价 / 历史行情的降级回退：AkShare
- 财务口径不允许由 AkShare 替代 Tushare 作为主事实来源

---

## 4. 关键改造项

### 4.1 市场与代码模型

统一引入以下字段：

- `market`: `US | CN_A`
- `exchange`: `NASDAQ | NYSE | SSE | SZSE | BSE`
- `currency`: `USD | CNY`
- `name`: 证券名称，可空

统一代码规范：

- 美股：继续使用 `NVDA` 这类 symbol
- A 股：强制使用带交易所后缀的 canonical symbol
  - `600519.SH`
  - `000001.SZ`
  - `430047.BJ`

约束：

- 系统内部所有流程使用 canonical symbol
- `coverage/` 路径直接使用 canonical symbol 作为目录名
  - 例如：`coverage/600519.SH/`
- 不做“自动猜测交易所”逻辑，避免歧义与误导

### 4.2 CSV 导入格式

将 `portfolio.csv` 升级为：

```csv
symbol,market,quantity,avg_cost
NVDA,US,10,800
600519.SH,CN_A,100,1680
```

兼容策略：

- 旧格式 `symbol,quantity,avg_cost` 继续支持
- 旧格式默认 `market=US`
- 若 `market=CN_A`，则 `symbol` 必须带 `.SH/.SZ/.BJ`
- 导入时要做显式校验并给出清晰报错

### 4.3 数据服务抽象

将现有 `app/services/market_data.py` 从单体封装改造成统一入口 + provider 适配层。

建议结构：

- `MarketDataService`
- `YFinanceProvider`
- `TushareProvider`
- `AkShareProvider`
- `FxProvider`

统一接口最少包括：

- `get_quote(symbol)`
- `get_batch_quotes(symbols)`
- `get_price_history(symbol, start, end, adjust_mode)`
- `get_security_master(symbol)`
- `get_fundamentals(symbol, period_or_latest)`
- `get_news_or_market_context(symbol, limit)`
- `get_fx_rate(from_currency, to_currency, date)`

路由规则：

- `US` → `yfinance`
- `CN_A` 主路径 → `Tushare`
- `CN_A` 补充或失败回退 → `AkShare`
- A 股财务数据不可用 AkShare 替代 Tushare 作为最终口径

### 4.4 组合估值与汇率

在 `profile` 中新增：

- `base_currency`

本次默认值：

- `USD`

组合层处理规则：

- 每个持仓保留本币价格与本币市值
- 所有组合级别计算先统一换算到 `base_currency`
- 权重、总资产、policy check 一律基于换算后的基准货币市值

每个持仓输出应增加：

- `local_price`
- `local_market_value`
- `fx_rate_to_base`
- `base_market_value`
- `price_source`

汇率处理规则：

- `USD/CNY` 使用 Tushare 日线外汇数据
- 当天缺值时回退最近可用交易日
- 回退时需显式标记 `fx_stale=true`

### 4.5 CLI 与工具脚本

以下命令全部改造成 market-aware：

- `portfolio add`
- `portfolio import`
- `portfolio summary`
- `portfolio refresh`
- `portfolio check`

以下脚本输出结构需要扩展：

- `app/tools/portfolio_tools.py`
- `app/tools/policy_tools.py`

重点要求：

- `portfolio_tools.py --refresh` 输出本币信息、汇率、基准货币市值、市场属性
- `policy_tools.py` 虽保留现有触发结构，但其判断依据改为换算后的 `base_market_value`

### 4.6 分析与建议链路

#### `analyze asset <SYMBOL>`

需要支持：

- 美股 symbol
- A 股 canonical symbol

A 股分析要求：

- 从 A 股 provider 获取市场上下文
- 不再复用美股默认 news 假设
- 若已存在 coverage，则继续按 thesis 做 IC 检查与三维分析

#### `analyze suggest`

需要支持：

- 混合持仓组合
- A 股 covered / uncovered 持仓
- 统一基准货币权重下的建议生成

要求：

- 对 covered A 股，注入 thesis 与头寸管理原则
- 对 uncovered A 股，维持“仅基于规则”的降级模式
- 输出中保留 “advisory only” 语义

### 4.7 Coverage / Researcher 适配

保留现有 thesis 模板结构：

- Fundamental
- Valuation
- Technical
- Invalidation Conditions
- 头寸管理原则
- 覆盖历史

需要改造：

- `researcher:initiate`
- `researcher:update`
- `researcher:analyze`
- `researcher:status`
- `pm:daily`
- `pm:suggest`

统一改造点：

- 命令先识别 `market`
- 再按市场切换数据源与数据质量规则
- 不再默认使用 `yfinance / Yahoo / StockAnalysis` 作为唯一研究路径

数据质量规则拆分：

- `US`：
  - 保留现有 yfinance / StockAnalysis 校验逻辑
- `CN_A`：
  - 财务、估值、复权统一以 Tushare 为准
  - AkShare仅用于市场补充信息，不承担财务口径责任

---

## 5. 建议的实施顺序

### Phase A — 底层能力先行
先完成不会影响上层工作流语义的底层抽象：

- 增加 `market / exchange / currency / name`
- 升级数据库模型与 JSON 输出
- 引入 `base_currency`
- 完成 FX 换算逻辑
- 抽象 market data provider 路由

目标：

- mixed portfolio 能正确刷新、汇总、计算权重

### Phase B — A 股持仓主链路
完成最基础但最有价值的用户链路：

- A 股导入
- A 股刷新
- A 股组合汇总
- A 股 policy check

目标：

- 你的 A 股持仓能真实进入系统并参与组合层规则判断

### Phase C — 分析与建议
在持仓链路稳定后再接分析：

- `analyze asset`
- `analyze suggest`
- `pm:daily`
- `pm:suggest`

目标：

- A 股也能得到和美股一致风格的分析与建议输出

### Phase D — Coverage / Researcher
最后接 thesis 与研究流：

- researcher 命令适配 A 股
- coverage 路径适配 canonical symbol
- A 股 thesis 数据质量规则补齐

目标：

- A 股纳入完整的长期研究管理体系

---

## 6. 文档与配置改造

需要同步更新：

- `README.md`
- `PROJECT_STATUS.md`
- `.claude/commands/pm/*.md`
- `.claude/commands/researcher/*.md`

需要新增或调整的配置：

- 环境变量：`TUSHARE_TOKEN`
- Python 依赖：
  - `tushare`
  - `akshare`

文档中必须新增：

- A 股导入示例
- mixed portfolio 示例
- `USD` 基准货币下的组合解释
- Tushare token 配置说明
- A 股 symbol 规范说明

---

## 7. 测试方案

### 7.1 回归测试
确保原有美股路径不被破坏：

- 旧版美股 CSV 可继续导入
- `portfolio refresh` 对美股仍正常
- `policy check` 对纯美股组合结果不变
- `analyze suggest` 旧行为不回归

### 7.2 A 股导入测试
覆盖以下场景：

- 新格式混合导入成功
- 旧格式导入默认 `US`
- `CN_A` 无交易所后缀时报错
- `.SH/.SZ/.BJ` 合法 symbol 可通过

### 7.3 汇率与组合测试
构造 `NVDA + 600519.SH` 混合组合，验证：

- 本币价格正确
- 本币市值正确
- 汇率正确
- USD 基准货币市值正确
- 总权重约等于 100%
- policy check 基于 USD 汇总结果触发

### 7.4 A 股分析测试
覆盖以下场景：

- `analyze asset 600519.SH` 可运行
- A 股 coverage 存在时可读取 thesis
- `researcher:initiate 600519.SH` 可生成 thesis 草稿
- `analyze suggest` 对 covered / uncovered A 股都能给出合理输出

### 7.5 容错测试
覆盖以下失败路径：

- Tushare 财务失败
- Tushare 报价失败但 AkShare 可回退
- 汇率当天缺失，回退到最近可用日
- coverage 缺失时建议退化到 rules-only 模式

---

## 8. 风险与注意事项

### 8.1 主要风险
- A 股不同源之间字段口径不完全一致
- A 股“新闻”类信息往往更接近公告、题材、资金流，不完全等同于美股新闻流
- 混合货币后，用户对“总资产”和“收益”的感知会与当前单市场视图不同
- 若后续加入港股，symbol / market 抽象必须保持克制，避免再次重构

### 8.2 控制策略
- 财务口径只认一个主事实源
- 回退只允许发生在行情与补充信息层
- 所有基准货币换算都显式展示 FX 来源与是否 stale
- thesis 模板不改结构，减少行为层变更面积

---

## 9. 明确假设

当前计划默认以下假设成立：

- 第一轮只支持 A 股股票与场内 ETF
- 基准货币使用 `USD`
- A 股代码必须使用带后缀 canonical symbol
- A 股分析中的“市场上下文”允许采用公告、题材、资金流等广义信息
- 系统仍是研究与决策辅助工具，不模拟真实交易执行限制

---

## 10. 建议的下一步

建议你先按以下顺序审阅：

1. 先看“总体方案”和“关键改造项”，确认方向是否正确
2. 再看“实施顺序”，确认你想先拿到哪一阶段的价值
3. 最后逐条修改“测试方案”和“明确假设”，把口径定死

如果后续进入执行阶段，建议第一批实现只做：

- 市场字段
- A 股导入
- 汇率换算
- A 股刷新
- 混合组合 summary / check

这样最快能把你的 A 股持仓真正纳入系统主流程。
