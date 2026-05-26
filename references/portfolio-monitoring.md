# Portfolio Monitoring — 组合监控

> 来源参考：Anthropic `financial-services` private-equity `portfolio-monitoring`，已改写为个人持仓和 watchlist thesis 监控框架。

## 触发

"组合监控"、"portfolio review"、"持仓复盘"、"组合表现"、"仓位风险"、"review positions"

## 一、目标

把单票 thesis、仓位、价格、催化剂、SMAM 动量和组合风险放在同一张表里。输出研究结论，不输出交易指令。

## 二、输入

| 数据 | 来源 |
|------|------|
| 持仓 | `memory/strategies/portfolio/positions-current.json`（优先）/ Longbridge positions / `positions-tracker.md` 兼容阅读版 |
| thesis | `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}/*.md` |
| 行情/估值 | Longbridge quote、valuation、kline |
| 新闻/催化剂 | Longbridge news、filing、catalyst-calendar |
| 动量 | `screen_momentum.py` / SMAM |

## 三、监控维度

| 维度 | 检查项 |
|------|--------|
| Thesis | Intact / Watch / Broken |
| Price | 当前价 vs 成本、目标价、止损、支撑阻力 |
| Fundamental | 财报、指引、利润率、现金流是否偏离预期 |
| Catalyst | 已发生/未发生/延期，结果是否符合预期 |
| Momentum | CMS、Stability、VAM、VM_Score |
| Risk | 单票集中度、行业集中度、相关性、流动性 |
| Actionability | 继续观察、复核 thesis、更新模型、移出 watchlist |

## 四、红黄绿规则

| 状态 | 条件 |
|------|------|
| Green | thesis intact，关键指标符合预期，SMAM 中性或正向 |
| Yellow | 单项偏离，如催化剂延期、动量转弱、估值过高 |
| Red | 逻辑破坏条件触发、财务恶化、SMAM Q5 且基本面反证 |

Yellow 需要说明“看什么数据会升级/降级”。Red 必须进入 thesis review。

## 五、输出格式

```markdown
## Portfolio Monitoring — YYYY-MM-DD

组合结论: [一句话]

| Symbol | Weight | P&L | Thesis | CMS | Catalyst | Risk Flag | Next Review |
|--------|--------|-----|--------|-----|----------|-----------|-------------|
| | | | Green/Yellow/Red | | | | |

重点变化:
1.
2.
3.

Red / Yellow 处理:
| Symbol | 问题 | 证据 | 下一步 |
|--------|------|------|--------|

组合风险:
- 行业集中度:
- 单票集中度:
- 相关性:
- 流动性:

以上仅供研究分析，不构成投资建议或交易指令。
```

## 六、复核频率

- 日内/盘前：只看价格、新闻、SMAM、重大催化。
- 周度：组合风险、持仓权重、watchlist 变化。
- 季度：逐票 thesis scorecard 和模型更新。
