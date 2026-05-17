# Returns Analysis — IRR / MOIC 回报归因

> 来源参考：Anthropic `financial-services` private-equity `returns-analysis`，用于 PE 式机会评估和特殊情景回报测算。

## 触发

"returns analysis"、"IRR"、"MOIC"、"回报测算"、"投资回报"、"LBO returns"、"back of envelope"

## 一、适用场景

- 特殊机会、重组、收购、私有化、spin-off。
- 判断一笔机会的 upside/downside 是否值得研究。
- 将收益来源拆成增长、估值、去杠杆、分红/回购。

## 二、输入

| 分类 | 输入 |
|------|------|
| Entry | 当前价格/EV、Entry multiple、净债务、市值 |
| Operating | Revenue growth、EBITDA margin、FCF、CapEx、NWC |
| Financing | Debt、利率、还款、回购/分红 |
| Exit | 持有期、Exit multiple、Exit EBITDA / EPS |
| Cost | 交易成本、税费、稀释、管理层激励 |

## 三、Base Case

| Metric | Value |
|--------|-------|
| Entry EV | |
| Entry equity value | |
| Exit EBITDA / EPS | |
| Exit EV / equity value | |
| Net debt at exit | |
| Interim cash returns | |
| MOIC | |
| IRR | |

## 四、回报归因

| Driver | Contribution | 说明 |
|--------|--------------|------|
| EBITDA / EPS growth | | 经营增长贡献 |
| Multiple expansion/contraction | | 估值变化贡献 |
| Debt paydown / net cash | | 资产负债表贡献 |
| Dividends / buybacks | | 现金回报 |
| Dilution / fees | | 拖累项 |

## 五、敏感性矩阵

常用 2-way：
- Entry multiple vs Exit multiple。
- EBITDA growth vs Exit multiple。
- Hold period vs Exit multiple。
- Revenue CAGR vs Margin。

单元格格式：`IRR / MOIC`。

## 六、三情景

| | Bear | Base | Bull |
|---|------|------|------|
| Revenue CAGR | | | |
| Exit margin | | | |
| Exit multiple | | | |
| Exit value | | | |
| MOIC | | | |
| IRR | | | |

## 七、输出格式

```markdown
## Returns Analysis — [标的/机会]

核心结论: [一句话]

| Scenario | MOIC | IRR | 关键假设 |
|----------|------|-----|----------|
| Bear | | | |
| Base | | | |
| Bull | | | |

回报归因:
1. Growth:
2. Multiple:
3. Balance sheet:
4. Cash returns:

最敏感变量:
- [变量] 每变化 X，对 IRR 影响 Y

以上仅供研究分析，不构成投资建议或交易指令。
```

## 八、边界

- PE 式 IRR/MOIC 是情景工具，不替代 DCF。
- 上市公司交易型机会必须同时看流动性、波动和催化剂时间窗口。
- 对杠杆交易，必须先看 downside 和再融资风险。
