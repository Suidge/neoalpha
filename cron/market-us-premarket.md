# Market US Premarket - 美股盘前模型策略制定

北京时间 20:30(美东 08:30)。

## 硬性要求

- 当前 cron run 内完成,禁止 spawn/subagent
- 工具静默,禁止输出过程；任何解释下一步、检查文件、等待命令的文字都算失败
- 必须先读取 compact 数据包,再由模型形成观点
- 必须写入 `memory/strategies/us-daily.md`
- 必须运行 `skills/investment-system/scripts/validate_us_strategy.py` 并看到通过结果
- 最终只输出一次盘前策略简报；未完成写入和校验前禁止结束

## 执行控制

- 如果 `exec` 返回命令仍在运行,必须使用 `process poll` / `process log` 等待同一个后台进程完成。
- 禁止因为命令仍在运行而启动重复的数据包或校验命令。
- 禁止假设脚本会自动写入策略文件；数据包 wrapper 只提供数据,策略文件必须由本 cron run 写入。
- 写入策略文件后必须重新读取或校验目标文件,确认包含今日标题、四段式结构和 `## 机器可读策略`。
- 机器可读代码块必须使用 ```proactive-trader-strategy,不能使用 ```json。
- 机器可读 JSON 顶层必须直接包含 `date`、`market`、`market_watch`、`monitors`,禁止包裹在 `strategy` 或 `proactive-trader-strategy` 字段下。
- 运行正式校验前,必须先用 Python `json.loads` 解析 ```proactive-trader-strategy 代码块内容；解析失败必须修复 JSON 语法后再继续。
- 校验失败时只能修正策略文件并重跑校验,不能输出盘前简报。
- 最终回复必须直接从盘前策略简报正文开始；禁止包含 `Validation passed`、`Now I output`、`Let me`、`I have`、`已完成校验` 等执行状态句。

## 执行步骤

1. 运行无参数数据包 wrapper:`skills/investment-system/scripts/build_us_premarket_pack.py`。
2. 基于数据包轻量研判:
   - **Preset 选股器**（数据包 `stock_screens` 字段）：读取 `short_term_momentum` 与 `long_term_compounder`，分别作为今日短线盯盘/试仓候选和中长线 thesis/DCF 优先级
   - **市场观察模板**（数据包 `market_watch_template` 字段）：先制定今日市场特征假设，再制定个股盯盘；盘中 live 会优先验证 `market_watch`
   - 宏观/指数、盘前真实报价、上一常规收盘、新闻标题
   - thesis 标的、owner prompt、structured positions（`portfolio/positions-current.json`，兼容字段名 `positions_tracker`）
   - 风险优先级
3. 写入 `memory/strategies/us-daily.md`,内容必须包含:

### 人类可读部分 — 四段式结构

```
# {日期} 美股盘前策略

## 📌 核心结论
[一句话定调 + 信号类型(🟢积极/🟡中性/🔴谨慎) + 仓位建议(加仓/持有/减仓)]

## 📊 数据视角
- 大盘趋势: [指数方向 + 短线/中长线选股器结果概览]
- 价格位置: [关键指数支撑/阻力]
- 量能判断: [成交量特征]
- 资金面: [宏观流动性线索]
- 市场特征: [risk-on/risk-off/恐慌/震荡/热点切换/动量断裂之一，并说明证据]

## 📰 情报汇总
- 关键新闻: [top 3]
- 风险警报: [宏观事件风险 + 短线选股器 Avoid Chase / 低分标的]
- 积极催化: [短线 Strong Watch / Setup Watch 标的 + 中长线 Thesis/DCF Candidate + 利好新闻]

## 🎯 作战计划
[先写市场观察剧本: 观察对象 | 盘前假设 | 验证信号 | 证伪信号 | 应对]
[再写重点标的表格: 标的 | 方向 | 狙击区间 | 仓位建议 | 操作清单]
[短线 Strong Watch / Setup Watch 标的优先列入积极关注；Avoid Chase 标的不建议新开仓]
```

- **选股器结论必须出现在数据视角和情报汇总中**
- **市场观察必须是主菜**：必须判断今天市场是否恐慌、是否 risk-on/risk-off、动量是否发生显著变化、热点板块是否切换；个股波动只能作为这些判断的证据或次级监控。
- **仓位意识必须进入作战计划**：已持仓标的要区分“持有/加仓/减仓/观察”，不要把持仓标的当作普通 watchlist；仓位数据来自数据包 `positions_tracker.positions`。
4. **选股器研判规则**：
   - `short_term_momentum` 的 `Strong Watch` / `Setup Watch` → 今日短线积极关注，进入作战计划
   - `short_term_momentum` 的 `Avoid Chase` → 不追高、不新开仓；若已持仓，只作为风险复核
   - `long_term_compounder` 的 `Thesis Candidate` / `DCF Candidate` → 中长线深研优先级，必要时进入 thesis/DCF 更新
   - 两个选股器共同高分 → 优先列入作战计划；短线高分但长线低分 → 只按交易型观察处理
5. 所有涉及个股的可读内容必须同时写代码和股票名称（如 `NVDA.US 英伟达`），不得只写代码。
6. JSON block 必须使用 ```proactive-trader-strategy 代码块；顶层必须直接是策略对象,不要再包一层 `strategy` 或 `proactive-trader-strategy` key。必须包含：
   - `market_watch.thesis`: 今日市场主假设
   - `market_watch.regime_hypotheses[]`: risk-on/risk-off/恐慌/轮动/震荡等假设、证据、证伪条件
   - `market_watch.benchmarks[]`: 指数/跨资产观察对象，每个包含 `symbol`、`name`、`role`、`triggers[]`
   - `market_watch.sector_rotation[]`: 热点/冷点板块观察
   - `market_watch.momentum_regime`: 基于 `stock_screens` 的短线/中长线强弱分布解释
   - `monitors[]`: 个股层面，每个 monitor 必须包含 `symbol`、`name`、`focus`、`triggers[]`
   **每个 symbol 必须保留完整后缀（如 NVDA.US），不得省略为裸 ticker。** JSON block 写在 `## 机器可读策略` 标题下、四段式人类可读部分之后。
7. 运行无参数校验 wrapper:`skills/investment-system/scripts/validate_us_strategy.py`。
8. 校验通过后,输出一条简洁盘前策略简报（四段式摘要）。最终回复只包含简报正文,不得包含校验状态或执行过程说明。若校验始终无法通过,最终回复必须明确以 `[FAILED]` 开头并说明阻断原因,不得伪装成成功简报。

## 报价与宏观规则

- 严格遵守数据包 `quote_interpretation_rules`，只在 `quote.pre_market` 非空时写盘前涨跌。
- `quote.regular_session.change_pct` 只能写成上一常规交易日涨跌。
- 必须检查 `macro_events`；high 重要性事件进入 Top Call、关键催化剂或风险。
- 数据包只有新闻标题时，标注为待确认，不得编造宏观数值或实时跨资产数据。

## 研判要求

- 不要机械保留所有默认触发器;按模型判断筛选/调整今日重点。
- 盘中 live 的观察优先级必须是：市场状态假设 → 大类资产/指数 → 板块轮动/动量扩散 → 持仓/个股触发。
- 触发器必须具体、可机器执行。
- **短线选股器信号优先用于今日加仓/减仓时机判断**，不与价格触发器冲突，两者互补。
- **策略 YAML 库参考**（`skills/investment-system/strategies/`）：如需调用特定策略框架，读取对应 YAML。
- 不确定的新闻或数据必须标注为待确认,禁止编造。
