# Market HK Premarket - 港股盘前模型策略制定

北京时间 08:30(港股开盘前 1 小时)。

## 硬性要求

- 当前 cron run 内完成,禁止 spawn/subagent
- 工具静默,禁止输出过程
- 必须先读取 compact 数据包,再由模型形成观点
- 必须写入 `memory/strategies/hk-daily.md`
- 最终只输出一次盘前策略简报

## 执行步骤

1. 运行无参数数据包 wrapper:`skills/investment-system/scripts/market_hk_pack.py`。
2. 基于数据包轻量研判:
   - **SMAM 动量扫描**（数据包 `momentum_scan` 字段）：读取 Q1(强动量)/Q4-Q5(负动量) 标的 → 作为加仓/减仓/观望信号融入策略。**港股任务同时扫描 .HK/.SZ/.SH 标的（A 股纳入港股盘前）**
   - 恒科/权重股、重要中概 ADR 隔夜表现、开盘前可用报价
   - 上一交易日收盘、港股新闻标题、thesis 标的、owner prompt、positions tracker
   - 风险优先级
3. 写入 `memory/strategies/hk-daily.md`,内容必须包含:

### 人类可读部分 — 四段式结构

```
# {日期} 港股盘前策略

## 📌 核心结论
[一句话定调 + 信号类型(🟢积极/🟡中性/🔴谨慎) + 仓位建议(加仓/持有/减仓)]
[港股开盘方向判断，结合隔夜中概ADR表现]

## 📊 数据视角
- 大盘趋势: [恒科方向 + SMAM 动量分布概览(含A股)]
- 价格位置: [关键指数支撑/阻力]
- 量能判断: [成交特征]
- 资金面: [南向资金线索 + 中概ADR隔夜]

## 📰 情报汇总
- 关键新闻: [top 3]
- 风险警报: [宏观事件 + SMAM Q4/Q5 预警标的(含A股)]
- 积极催化: [SMAM Q1 强动量标的(含A股) + 利好新闻]

## 🎯 作战计划
[重点标的表格: 标的 | 方向 | 狙击区间 | 仓位建议 | 操作清单]
[港股标的 + A股标的统一排序，按 SMAM CMS 降序]
[SMAM Q1 标的优先列入积极关注，Q4/Q5 标的不建议新开仓]
```

- **SMAM 结论必须出现在数据视角和情报汇总中**
4. **SMAM 研判规则**：
   - Q1 标的（CMS>0.84, Stability≥0.8）→ 标记为"动量加仓窗口"，列入作战计划积极关注
   - Q4/Q5 标的（CMS<-0.25）→ 标记为"动量预警"，列入情报汇总风险部分
   - A 股标的（.SZ/.SH）与港股标的统一排序，按 CMS 降序排列
5. 所有涉及个股的可读内容必须同时写代码和股票名称（如 `700.HK 腾讯控股`），不得只写代码。
6. JSON block 顶层必须直接是策略对象,不要再包一层 `proactive-trader-strategy` key;每个 monitor 必须包含 `symbol`、`name`、`focus`、`triggers[]`。**每个 symbol 必须保留完整后缀（如 700.HK），不得省略为裸数字或短码。** JSON block 写在 `## 机器可读策略` 标题下、四段式人类可读部分之后。
7. 运行无参数校验 wrapper:`skills/investment-system/scripts/market_hk_validate.py`。
8. 校验通过后,输出一条简洁盘前策略简报（四段式摘要 + 含A股动量概览）。

## 报价与 ADR 规则

- 严格遵守数据包 `quote_interpretation_rules`，只在 `quote.pre_market` 非空时写港股开盘前涨跌。
- `quote.regular_session.change_pct` 只能写成上一常规交易日涨跌。
- `hk_overnight_us_context` 是港股盘前必看项，必须进入 Top Call 或市场方向判断。
- ADR/中概 ETF 只能写成隔夜美股中概情绪/港股开盘线索，不得写成港股盘前报价。
- 数据包只有新闻标题时，标注为待确认，不得编造南向、夜期或宏观数值。

## 研判要求

- 不要机械保留所有默认触发器;按模型判断筛选/调整今日重点。
- 触发器必须具体、可机器执行。
- **SMAM 动量信号优先用于加仓/减仓时机判断**，不与价格触发器冲突，两者互补。
- **策略 YAML 库参考**（`skills/investment-system/strategies/`）：如需调用特定策略框架，读取对应 YAML。
- **A 股标的（.SZ/.SH）的 SMAM 结果与港股并列展示**，不给独立的 A 股板块。
- 不确定的新闻或数据必须标注为待确认,禁止编造。
