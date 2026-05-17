# Market US Close — 美股收盘复盘

美东工作日 16:00 执行；用于收盘复盘，避免与盘中巡检重叠。

## 硬性要求

- 当前 cron run 内完成，禁止 spawn/subagent
- 工具静默，禁止输出过程
- 只输出一次最终简报；非交易日输出 `NO_REPLY`；简报必须基于 live-state 汇总全天增量，避免机械列全量触发器

## 执行说明

执行无参数 wrapper：`skills/investment-system/scripts/market_us_close.py`。

## 成功标准

- 读取 `memory/strategies/us-daily.md` 中的结构化策略
- 对照 live-state 与收盘行情输出全天摘要，包括异动 Top、盘中报警回顾、静默监控数量
