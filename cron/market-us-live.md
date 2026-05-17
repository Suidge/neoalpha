# Market US Live — 美股盘中巡检

美东工作日 09:00-15:30 每 30 分钟执行；收盘复盘由 `market-us-close` 在 16:00 单独执行。

## 硬性要求

- 当前 cron run 内完成，禁止 spawn/subagent
- 工具静默，禁止输出过程
- 默认 `NO_REPLY`；首次触发、级别升级、价格/涨跌幅显著扩大或数据质量异常时输出详细增量警报；已报警条件再次命中时只输出一行简报

## 执行说明

执行无参数 wrapper：`skills/investment-system/scripts/market_us_live.py`。

## 输出规则

- wrapper 输出 `NO_REPLY` 时，最终回复必须只包含 `NO_REPLY`
- wrapper 输出播报时，原样输出；禁止补充机械复述
