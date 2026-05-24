# Architecture — Investment System

**版本**: 3.0.0 (2026-05-17)

## 核心理念

脚本负责读数据和校验结构，模型负责盘前主动制定“市场观察剧本 + 个股监控”，盘中脚本按策略 JSON 确定性判断，盘后闭环复盘；禁止交易执行。盘中主线是市场状态验证/证伪，个股波动是证据层。

## 数据流

```text
盘前 cron → build_{us,hk}_premarket_pack.py（compact pack；stock_screens；medium_term_health；market_watch_template；HK 额外采集中概 ADR 隔夜线索与A股指数；可选 prompt/结构化 positions 注入）→ 模型主动研判 → memory/strategies/{market}-daily.md → validate wrapper
     ↓
盘中 cron → run_{us,hk}_live_check.py → market_watch + monitor triggers + live-state 分层播报 → NO_REPLY / 市场观察 / 个股警报 / 一行复触发简报
     ↓
盘后 cron → generate_{us,hk}_close_review.py → live-state + 收盘行情 → 全天摘要 → 次日策略输入
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
│   ├── market_strategy_engine.py
│   ├── portfolio_ledger.py
│   ├── screen_momentum.py
│   ├── screen_stocks.py
│   ├── build_dcf_model.py
│   ├── validate_dcf.py
│   ├── analyze_earnings_preview.py
│   ├── analyze_earnings_recap.py
│   ├── build_{us,hk}_premarket_pack.py
│   ├── validate_{us,hk}_strategy.py
│   ├── run_{us,hk}_live_check.py
│   └── generate_{us,hk}_close_review.py
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
memory/strategies/portfolio/transactions.csv
memory/strategies/portfolio/instruments.yaml
memory/strategies/portfolio/positions-current.json
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

必备 JSON 字段：`schema_version`, `date`, `market`, `market_watch`, `monitors[]`。

`market_watch` 是盘中主控层，至少包含：
- `thesis`：今日市场主假设。
- `regime_hypotheses[]`：risk-on/risk-off/恐慌/轮动/震荡等假设、证据、证伪条件。
- `benchmarks[]`：指数/跨资产/A股指数观察对象，支持与 `monitors[]` 相同的 `triggers[]`。
- `sector_rotation[]`：热点/冷点板块观察。
- `momentum_regime`：SMAM 强弱分布对市场动量的解释。
- `medium_term_health`：中期大盘健康度状态、风险等级、关键收复位/失效位和仓位进攻性约束。

每个 monitor 至少包含 `symbol`, `name`, `focus`, `triggers[]`。所有个股相关可读汇报必须同时显示代码和股票名称。HK 策略允许 `.HK/.SZ/.SH`，用于覆盖同段交易的 A 股。

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

盘前任务保持 `isolated`，确保每天策略制定不被旧上下文污染。盘前数据包会读取可选的主人额外 prompt：`memory/strategies/us-premarket-prompt.md` 或 `memory/strategies/hk-premarket-prompt.md`；文件不存在或为空时不注入，存在时按脚本上限截断。仓位数据优先读取 `memory/strategies/portfolio/positions-current.json`，并以 `positions_tracker.positions` 注入；`positions-tracker.md` 只作为脚本生成的人类阅读版和兼容兜底。盘前数据包会提供 `market_watch_template`，要求模型先写市场主假设、市场特征、板块轮动、动量状态和证伪条件，再写个股监控。港股盘前会同时纳入 .HK/.SZ/.SH 持仓与 A股指数（上证、深成、创业板、沪深300）。港股盘前必须额外读取 `hk_overnight_us_context`：金龙/中概互联网 ETF 与腾讯、阿里、美团、小米 ADR 隔夜美股表现，用于判断恒科开盘情绪；这些数据只能作为隔夜中概情绪线索，不得等同于港股盘前报价。

## Portfolio Ledger

持仓记录采用 ledger-first：

```text
memory/strategies/portfolio/transactions.csv       # 唯一事实来源：每笔交易
memory/strategies/portfolio/instruments.yaml       # 标的静态信息
memory/strategies/portfolio/positions-current.json # 脚本生成：当前仓位
memory/strategies/positions-tracker.md             # 脚本生成：阅读版/兼容旧路径
```

自然语言仓位变动必须通过 `scripts/portfolio_ledger.py record "<描述>"` 写入，例如 `14.49买进1000股POET` 会解析为 `BUY 1000 POET.US @ 14.49`，追加交易流水并重建快照。当前持仓、均价、成本和已实现盈亏不得手工编辑。

美股 cron 全部使用 `America/New_York` 时区，港股 cron 全部使用 `Asia/Hong_Kong` 时区；US live 不再需要 overnight 拆分任务。reset cron 只改 live/close cron 的 `sessionTarget`，不删除 transcript 文件。

## Cron 设计

Cron payload 只负责读取对应 `cron/market-*.md`。盘前 cron 必须用模型分析 compact pack 并写策略；报价解释规则在 pack 顶层只给一次，避免每个 monitor 重复消耗 token。盘中/盘后 cron 调用轻量 wrapper，避免大上下文 LLM 临场推理导致超时。盘中 wrapper 必须把已报警状态写入 `memory/strategies/{market}-live-state-YYYY-MM-DD.json`：优先评估 `market_watch` 的市场假设、指数/跨资产/A股指数触发器和板块轮动观察；随后评估 `monitors[]` 个股触发器。首次触发、级别升级或价格/涨跌幅显著扩大时输出详细警报；已报警条件再次命中时只输出一行代码+名称+价格+涨跌幅简报；无命中输出 `NO_REPLY`。
