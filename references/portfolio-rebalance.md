# Portfolio Rebalance — 组合再平衡

> 来源参考：Anthropic `financial-services` wealth-management `portfolio-rebalance`，已改写为研究型组合漂移分析。

## 触发

"再平衡"、"rebalance"、"portfolio drift"、"仓位偏离"、"配置比例"、"组合太偏"

## 一、目标

识别组合实际暴露与目标暴露的偏离，评估风险与税费影响。输出建议研究动作，不直接生成交易指令。

## 二、目标配置

若用户没有明确 IPS/目标配置，先用当前策略文件或用户偏好作为临时基准，并标记 `[ASSUMPTION]`。

持仓输入优先使用 `memory/strategies/portfolio/positions-current.json`。不要从 `positions-tracker.md` 反推仓位，后者只是脚本生成的阅读版。

| 维度 | 示例 |
|------|------|
| 市场 | US / HK / A股 / Cash |
| 行业 | AI、电力、半导体、消费、医药、金融 |
| 风格 | Growth / Value / Quality / Momentum / Special Situation |
| 单票上限 | 如 10%-20%，由用户规则决定 |
| 现金下限 | 如 5%-15%，由市场环境决定 |

## 三、Drift Analysis

| Exposure | Target % | Current % | Drift | Status |
|----------|----------|-----------|-------|--------|
| US Equity | | | | Within / Over / Under |
| HK Equity | | | | |
| AI Infra | | | | |
| Cash | | | | |

默认阈值：
- 单类资产偏离 >5pp：Yellow。
- 单类资产偏离 >10pp：Red。
- 单票超过上限：Red。
- 同主题高度相关持仓合计过高：Yellow/Red，视波动和流动性。

## 四、再平衡优先级

1. 先用新增现金/分红/自然减仓修正，减少交易成本。
2. 先处理 Red：逻辑破坏、集中度过高、流动性差。
3. 税务账户中避免为了小漂移卖出大额短期收益。
4. 若 drift 来自赢家上涨，先确认 thesis 是否仍 intact。
5. 若 drift 来自亏损扩大，先确认是否触发逻辑破坏条件。

## 五、输出格式

```markdown
## Portfolio Rebalance Review — YYYY-MM-DD

结论: [无需调整 / 观察 / 需要再平衡研究]

| Exposure | Target | Current | Drift | Flag | 说明 |
|----------|--------|---------|-------|------|------|

候选动作（研究层面）:
| 动作 | 标的/资产 | 理由 | 风险/成本 |
|------|-----------|------|----------|
| Add / Trim / Hold / Review | | | |

优先复核:
1.
2.
3.

以上仅供研究分析，不构成投资建议或交易指令。
```

## 六、边界

- 不代替用户做实际交易。
- 不做税务建议，只标记潜在税费影响。
- 若需要真实下单，必须另行确认。
