# Market US Live — 美股盘中巡检

美东工作日 09:00-15:30 每 30 分钟执行；09:00-09:29 为预开盘静默窗口，wrapper 必须返回 `NO_REPLY`，避免把上一常规交易日涨跌当作当日盘中涨跌；收盘复盘由 `market-us-close` 在 16:00 单独执行。

## 硬性要求

- 当前 cron run 内完成，禁止 spawn/subagent
- 工具静默，禁止输出过程
- 默认 `NO_REPLY`；首次触发、级别升级、价格/涨跌幅显著扩大或数据质量异常时输出详细增量警报；已报警条件再次命中时只输出一行简报
- 盘中输出优先级：`market_watch` 市场假设验证/证伪 > 大类资产/指数变化 > 板块轮动/动量扩散 > 个股触发器
- 个股波动必须尽量解释为市场观察证据；不要把单票涨跌当作主菜

## 执行说明

执行无参数 wrapper：`skills/investment-system/scripts/run_us_live_check.py`。

wrapper 会读取当日 `memory/strategies/us-daily.md` 的机器可读策略：
- `market_watch`: 盘前市场主假设、risk-on/risk-off/恐慌/轮动/震荡观察、指数/跨资产触发器
- `monitors`: 个股/持仓触发器

若 `market_watch` 存在，首次盘中 run 会输出一次市场假设跟踪快照；之后只在市场观察触发、级别升级或偏离扩大时输出。

## 输出规则

- wrapper 输出 `NO_REPLY` 时，最终回复必须只包含 `NO_REPLY`
- wrapper 输出播报时，原样输出；禁止补充机械复述
