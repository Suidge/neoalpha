# Architecture — Investment System

**版本**: 3.0.0 (2026-05-17)

## 核心理念

脚本负责读数据和校验结构，模型负责盘前主动制定策略，盘中脚本按策略 JSON 确定性判断，盘后闭环复盘；禁止交易执行。

## 数据流

```text
盘前 cron → market_{us,hk}_pack.py（compact pack；HK 额外采集中概 ADR 隔夜线索；可选 prompt/positions 截断注入）→ 模型主动研判 → memory/strategies/{market}-daily.md → validate wrapper
     ↓
盘中 cron → market_{us,hk}_live.py → JSON triggers + live-state 分层播报 → NO_REPLY / 详细警报 / 一行复触发简报
     ↓
盘后 cron → market_{us,hk}_close.py → live-state + 收盘行情 → 全天摘要 → 次日策略输入
```

## 文件结构

```text
skills/investment-system/
├── SKILL.md
├── INSTALLATION.md
├── cron/
│   ├── market-us-premarket.md
│   ├── market-us-live.md
│   ├── market-us-close.md
│   ├── market-hk-premarket.md
│   ├── market-hk-live.md
│   ├── market-hk-close.md
│   ├── market-us-session-reset.md
│   └── market-hk-session-reset.md
├── scripts/
│   ├── proactive_trader.py
│   ├── momentum_scanner.py
│   ├── build_dcf_model.py
│   ├── validate_dcf.py
│   ├── earnings_preview.py
│   ├── earnings_recap.py
│   ├── market_{us,hk}_pack.py
│   ├── market_{us,hk}_validate.py
│   ├── market_{us,hk}_live.py
│   └── market_{us,hk}_close.py
├── strategies/
│   └── *.yaml
├── templates/
│   └── thesis-template.md
├── references/
├── thesis-tracker/
└── tracking/
```

Runtime strategy files:

```text
memory/strategies/us-daily.md
memory/strategies/hk-daily.md
memory/strategies/{us,hk}-premarket-prompt.md
memory/strategies/positions-tracker.md
memory/strategies/{us,hk}-live-state-YYYY-MM-DD.json
```

## 当日策略格式

策略文件同时给人读和机器读。机器读部分必须使用 fenced block：

```text
```proactive-trader-strategy
{ ... JSON ... }
```
```

必备 JSON 字段：`schema_version`, `date`, `market`, `symbols`, `monitors[]`。每个 monitor 至少包含 `symbol`, `name`, `focus`, `triggers[]`。所有个股相关可读汇报必须同时显示代码和股票名称。

## 触发器类型

| type | 含义 |
|------|------|
| `pct_change_abs_gte` | 日内绝对涨跌幅超过阈值 |
| `pct_change_above` | 涨幅超过阈值 |
| `pct_change_below` | 跌幅超过阈值 |
| `price_above` | 价格突破上方价位 |
| `price_below` | 价格跌破下方价位 |

## 外部依赖

| 依赖 | 用途 |
|------|------|
| longbridge CLI | 行情、新闻、交易日、市场状态 |
| `skills/investment-system/thesis-tracker/` | 长期论点与关注标的 |
| `memory/strategies/` | 当日策略文件 |

## Session Lifecycle

盘中/收盘任务使用持久 session 来保持单日上下文连贯：

| 市场 | 共享 session | 覆盖任务 | Reset cron |
|------|--------------|----------|------------|
| US | `session:market-us-live-<date>` | market-us-live, market-us-close | market-us-session-reset, 19:15 America/New_York |
| HK | `session:market-hk-live-<date>` | market-hk-live, market-hk-close | market-hk-session-reset, 19:15 Asia/Hong_Kong |

盘前任务保持 `isolated`，确保每天策略制定不被旧上下文污染。盘前数据包会读取可选的主人额外 prompt：`memory/strategies/us-premarket-prompt.md` 或 `memory/strategies/hk-premarket-prompt.md`；文件不存在或为空时不注入，存在时按脚本上限截断。`positions-tracker.md` 同样只注入本市场符号和压缩内容。港股盘前必须额外读取 `hk_overnight_us_context`：金龙/中概互联网 ETF 与腾讯、阿里、美团、小米 ADR 隔夜美股表现，用于判断恒科开盘情绪；这些数据只能作为隔夜中概情绪线索，不得等同于港股盘前报价。

美股 cron 全部使用 `America/New_York` 时区，港股 cron 全部使用 `Asia/Hong_Kong` 时区；US live 不再需要 overnight 拆分任务。reset cron 只改 live/close cron 的 `sessionTarget`，不删除 transcript 文件。

## Cron 设计

Cron payload 只负责读取对应 `cron/market-*.md`。盘前 cron 必须用模型分析 compact pack 并写策略；报价解释规则在 pack 顶层只给一次，避免每个 monitor 重复消耗 token。盘中/盘后 cron 调用轻量 wrapper，避免大上下文 LLM 临场推理导致超时。盘中 wrapper 必须把已报警状态写入 `memory/strategies/{market}-live-state-YYYY-MM-DD.json`：首次触发、级别升级或价格/涨跌幅显著扩大时输出详细警报；已报警条件再次命中时只输出一行代码+名称+价格+涨跌幅简报；无命中输出 `NO_REPLY`。
