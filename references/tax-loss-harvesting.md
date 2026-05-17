# Tax-Loss Harvesting — 税损收割研究提示

> 来源参考：Anthropic `financial-services` wealth-management `tax-loss-harvesting`。本文件只用于研究提示，不构成税务建议。

## 触发

"税损收割"、"tax-loss harvesting"、"TLH"、"unrealized loss"、"harvest losses"、"年末税务"

## 一、目标

识别 taxable account 中可能有研究价值的未实现亏损，并提示 wash sale 等风险。实际税务处理必须由用户或专业税务顾问确认。

## 二、候选识别

| Security | Cost Basis | Current Value | Unrealized Loss | % Loss | Holding Period | Account |
|----------|------------|---------------|-----------------|--------|----------------|---------|
| | | | | | ST/LT | |

优先级：
1. 绝对亏损金额大。
2. 短期亏损优先级高于长期亏损。
3. 百分比亏损大且 thesis 已 broken。
4. 可用替代品维持类似暴露。

## 三、替代暴露

| Sell Candidate | Replacement | Exposure Match | Tracking Error | Wash Sale Risk |
|----------------|-------------|----------------|----------------|----------------|
| 个股 | 行业 ETF / peer basket | 低/中/高 | 低/中/高 | 低/中/高 |

原则：
- 个股替代为同行 basket 或行业 ETF，降低“实质相同”风险。
- ETF 替代必须避免同一指数/同一发行商高度相同产品。
- 检查账户内自动再投资、近期买入、配偶/家庭账户。

## 四、Wash Sale 检查

| Sold Security | Window Start | Window End | Recent Buy? | DRIP? | Risk |
|---------------|--------------|------------|-------------|-------|------|
| | T-30 | T+30 | | | |

## 五、输出格式

```markdown
## Tax-Loss Harvesting Watchlist — YYYY-MM-DD

声明: 以下仅为研究提示，不构成税务建议。

| Security | Unrealized Loss | % Loss | Thesis Status | Replacement Idea | Wash Sale Risk |
|----------|-----------------|--------|---------------|------------------|----------------|

优先复核:
1.
2.
3.

需要用户/税务顾问确认:
- 实际成本基础
- 账户类型
- 过去 30 天交易
- 未来 30 天再买入计划
```

## 六、边界

- 不计算最终税表。
- 不判断用户税率。
- 不执行交易。
- 不把 TLH 作为卖出理由；先看 thesis 是否 broken 或组合是否需要再平衡。
