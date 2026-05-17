# Unit Economics — 收入质量与客户经济性

> 来源参考：Anthropic `financial-services` private-equity `unit-economics`，适用于 SaaS、订阅、平台、交易型和混合商业模式。

## 触发

"unit economics"、"收入质量"、"ARR"、"NDR"、"LTV/CAC"、"cohort analysis"、"Rule of 40"、"SaaS 分析"

## 一、先识别商业模式

| 模式 | 重点 |
|------|------|
| SaaS / Subscription | ARR、NDR、GRR、cohort、CAC payback |
| Recurring services | 合同续约、ACV、客户集中度 |
| Transaction / usage | GMV、take rate、交易频次、单位履约成本 |
| Marketplace / Platform | 供需两侧增长、留存、网络效应、补贴率 |
| Hybrid | 拆分订阅、服务、硬件、一次性收入 |

## 二、核心指标

### ARR / Revenue Quality

| 指标 | 说明 |
|------|------|
| ARR bridge | Beginning ARR + New + Expansion - Contraction - Churn = Ending ARR |
| Cohort retention | 每年 cohort 后续收入保留和扩张 |
| Recurring % | 经常性收入占比 |
| Customer concentration | Top 10/20/50 客户占比 |
| Contract structure | ACV、multi-year、auto-renewal |

### Customer Economics

| 指标 | 公式 / 阈值 |
|------|------------|
| CAC | Sales & Marketing / New customers |
| LTV | ARPU x Gross Margin / Churn Rate |
| LTV:CAC | >3x 健康，>5x 优秀，<2x 警惕 |
| CAC payback | <12 月优秀，<18 月良好，>24 月警惕 |
| SaaS Magic Number | Net new ARR / prior S&M，>0.75x 较好 |

### Retention

| 指标 | 说明 |
|------|------|
| GRR | 不含 expansion 的收入保留 |
| NDR / NRR | 含 expansion 的收入保留 |
| Logo churn | 客户数量流失 |
| Dollar churn | 收入流失 |
| Expansion rate | Upsell / cross-sell 占 beginning ARR |

阈值：
- NDR >120%：优秀。
- NDR >110%：良好。
- NDR <100%：警惕。
- GRR <85%：高流失风险。

## 三、Cohort Matrix

```markdown
| Cohort | Year 0 | Year 1 | Year 2 | Year 3 | Year 4 |
|--------|--------|--------|--------|--------|--------|
| 2022 | 100 | 112 | 121 | | |
| 2023 | 100 | 108 | | | |
| 2024 | 100 | | | | |
```

同时看绝对金额和 indexed view。NDR 高但 GRR 低时，说明 expansion 掩盖了流失。

## 四、Revenue Quality Score

| Factor | Score (1-5) | Notes |
|--------|-------------|-------|
| Recurring % | | |
| NDR / GRR | | |
| Customer concentration | | |
| Cohort stability | | |
| Growth durability | | |
| Margin profile | | |
| CAC efficiency | | |
| **Overall** | | |

解释：
- 30+：高质量收入。
- 22-29：可接受，需跟踪弱项。
- <22：收入质量风险较高。

## 五、投资含义

必须回答：
- 增长是否靠健康获客驱动？
- 留存是否足以支撑长期复利？
- 毛利和 CAC 是否允许规模化盈利？
- 是否存在客户集中度或 cohort 衰退风险？
- 估值是否已反映收入质量？

## 六、输出格式

```markdown
## Unit Economics — [公司]

商业模式: [SaaS / Usage / Hybrid]
核心结论: [一句话]

| Metric | Value | Benchmark | 结论 |
|--------|-------|-----------|------|
| ARR growth | | | |
| NDR | | >110% | |
| GRR | | >90% | |
| LTV:CAC | | >3x | |
| CAC payback | | <18mo | |
| Rule of 40 | | >40 | |

Revenue Quality Score: X/35

关键风险:
1.
2.
3.

以上仅供研究分析，不构成投资建议或交易指令。
```
