---
name: investment-system
slug: investment-system
version: 3.0.0
description: Analyze stocks, build investment theses, run momentum scans, and execute multi-market trading strategies with DCF valuation and cron-based monitoring.
---

# Investment System — 统一投资分析系统

> v3.0.0 | 合并 financial + proactive-trader | 2026-05-16

## When to Use

投资研究/交易决策支持场景。具体入口见下方 Quick Reference。



## Core Rules

1. **所有数字必须验证** — Longbridge CLI 优先；web_search 只补充；标注来源与日期
2. **先路由再编排** — 本技能覆盖全面，但具体数据获取优先 Longbridge 和 sibling skills
3. **三情景输出** — DCF/LBO/财报前瞻必须提供 Bear / Base / Bull
4. **四条底线**: 先事实后推断 / 先验证后判断 / 先风控后收益 / 盈亏比量化
5. **SMAM 优先**: 盘前策略必须融入 SMAM 动量扫描结果

## Quick Reference

| 主人说... | 章节 | 详情见 |
|-----------|------|--------|
| 数据怎么取 / 来源怎么降级 | A0 | [references/data-layer.md](references/data-layer.md) |
| "财报分析 [公司]" | A1 | [references/earnings-workflow.md](references/earnings-workflow.md) |
| "财报前瞻 [公司]" | A2 | [references/earnings-preview.md](references/earnings-preview.md) |
| "晨会" | A3 | [references/morning-note.md](references/morning-note.md) |
| "thesis / 论点" | A4 | [references/thesis-tracker.md](references/thesis-tracker.md) |
| thesis 增强框架（Step 0-8） | A4-E | [references/thesis-framework-enhanced.md](references/thesis-framework-enhanced.md) |
| "催化剂" | A5 | [references/catalyst-calendar.md](references/catalyst-calendar.md) |
| "行业概览" | A6 | [references/sector-overview.md](references/sector-overview.md) |
| "竞争格局 / moat / market map" | A6-B | [references/competitive-landscape.md](references/competitive-landscape.md) |
| "选股 / Quantitative Screens / /screen" | A7 | [references/idea-generation.md](references/idea-generation.md) |
| "首次覆盖 / initiate coverage" | A8 | [references/initiating-coverage.md](references/initiating-coverage.md) |
| "tear sheet / 公司速览" | A9 | [references/tear-sheet.md](references/tear-sheet.md) |
| "DCF / 估值模型" | B1 | [references/dcf-model.md](references/dcf-model.md) |
| "可比公司" | B2 | [references/comps-analysis.md](references/comps-analysis.md) |
| "相关性 / 同涨同跌 / 持仓相关性" | B2-B | [references/correlation-analysis.md](references/correlation-analysis.md) |
| "流动性 / 价差 / 成交额" | B2-C | [references/liquidity-analysis.md](references/liquidity-analysis.md) |
| "SEPA / Minervini / 趋势模板 / VCP" | B2-D | [references/sepa-strategy.md](references/sepa-strategy.md) |
| "LBO" | B3 | [references/lbo-model.md](references/lbo-model.md) |
| "三张表" | B4 | [references/3-statement-model.md](references/3-statement-model.md) |
| "更新模型" | B5 | [references/model-update.md](references/model-update.md) |
| "SMAM" / 动量扫描 | B6 | [references/momentum-model.md](references/momentum-model.md) |
| "模型审计 / debug model / QA spreadsheet" | B6-A | [references/model-audit.md](references/model-audit.md) |
| "unit economics / ARR / NDR / LTV:CAC" | B6-B | [references/unit-economics.md](references/unit-economics.md) |
| "IRR / MOIC / returns analysis" | B6-C | [references/returns-analysis.md](references/returns-analysis.md) |
| 动量扫描脚本用法 | B6-S | `scripts/momentum_scanner.py --help` |
| 财报前瞻脚本 | B7-S | `scripts/earnings_preview.py <SYMBOL> --output text` |
| 财报复盘脚本 | B7-S | `scripts/earnings_recap.py <SYMBOL> --output text` |
| 策略 YAML 库 | B7 | [strategies/](strategies/) |
| "组合监控 / portfolio review" | D1 | [references/portfolio-monitoring.md](references/portfolio-monitoring.md) |
| "再平衡 / portfolio drift" | D2 | [references/portfolio-rebalance.md](references/portfolio-rebalance.md) |
| "税损收割 / TLH" | D3 | [references/tax-loss-harvesting.md](references/tax-loss-harvesting.md) |
| Excel 颜色/公式规范 | C1 | [references/excel-conventions.md](references/excel-conventions.md) |
| Excel 文件生成工具链 | C2 | [references/excel-toolchain.md](references/excel-toolchain.md) |

## External Endpoints

| Service | Purpose | Auth |
|---------|---------|------|
| `longbridge` CLI | 实时行情、k-line、财报、consensus、预告、估值等全量数据 | OAuth token (`~/.longbridge/openapi/tokens/`) |
| `openclaw` built-in tools | 可选补充数据（web_search、reading） | 内置 |

## Data Storage

- thesis 文件 → `skills/investment-system/thesis-tracker/<SYMBOL>.<MARKET>.md`
- 每日策略 → `memory/strategies/{us,hk}-daily.md`
- 持仓记录 → `memory/strategies/positions-tracker.md`
- 盘前 owner prompt → `memory/strategies/{us,hk}-premarket-prompt.md`
- 策略 YAML → `skills/investment-system/strategies/*.yaml`

## Related Sibling Skills

- `longbridge` / Longbridge 系列 — 实时行情、新闻、持仓、估值分位
- `github` — GitHub 操作
- `outlook-calendar` — 日历/日程管理
