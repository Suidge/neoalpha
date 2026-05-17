# DCF Model — 现金流折现估值

## 触发

"DCF"、"估值模型"、"内在价值"、"目标价怎么算"、"三情景估值"

## 输出目标

给出 Bear / Base / Bull 三情景下的企业价值、股权价值、每股内在价值、相对当前股价的溢价/折价，并展示核心假设与敏感性。

## 工作流

### Step 1: 数据收集与口径确认

优先读取 [data-layer.md](data-layer.md)。至少确认：

- 历史收入、EBIT/EBITDA、D&A、CapEx、NWC 或 CFO/FCF
- 净债务 = 总债务 - 现金；如有少数股东权益/优先股，需从 EV 桥接中扣除
- 稀释股本数
- 当前股价和市值
- 行业/公司生命周期：高增长、成熟、周期、亏损转盈

→ 若用户要求生成 Excel，先展示数据块并确认。

### Step 2: 预测经营结果

标准 5–10 年显性预测：

- Revenue_t = Revenue_{t-1} × (1 + Growth_t)
- EBIT_t = Revenue_t × EBIT Margin_t
- Tax_t = EBIT_t × Cash Tax Rate_t（亏损公司需考虑 NOL/转正年份）
- NOPAT_t = EBIT_t - Tax_t

增长率应从公司历史、管理层指引、行业增速逐步回归到终端增长率。

### Step 3: 计算自由现金流

Unlevered FCF：

```text
FCF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔNWC
```

若直接使用公司披露 FCF，必须说明口径，并避免和 EBIT 法混用。

### Step 4: WACC

```text
Cost of Equity = Risk-free Rate + Beta × Equity Risk Premium + Country/Size Premium
After-tax Cost of Debt = Pre-tax Cost of Debt × (1 - Tax Rate)
WACC = E/(D+E) × Cost of Equity + D/(D+E) × After-tax Cost of Debt
```

典型参数：

| 参数 | 获取/范围 |
|------|-----------|
| 无风险利率 | 使用 web_search 搜索 `10 year treasury yield today`，标注日期 |
| ERP | 成熟市场 5.0–6.0%；新兴市场额外 +1–3% |
| Beta | 使用 Longbridge/可靠金融数据或 web_search 搜索 `[SYMBOL] 5 year beta` |
| 税率 | 法定税率或长期有效税率；美国通常 21–28% |

### Step 5: 终值

两种方法至少选一种，成熟公司优先永续增长法；周期/交易导向可补退出倍数法。

```text
Terminal Value (Gordon) = FCF_final × (1 + g) / (WACC - g)
Terminal Value (Exit Multiple) = EBITDA_final × Exit EV/EBITDA
```

硬约束：终端增长率 `g < WACC`，且通常不应高于长期无风险利率。

### Step 6: 折现与股权价值桥接

```text
PV FCF_t = FCF_t / (1 + WACC)^t
PV TV = Terminal Value / (1 + WACC)^n
Enterprise Value = Σ PV FCF + PV TV
Equity Value = Enterprise Value - Net Debt - Minority Interest - Preferred Equity + Non-operating Assets
Intrinsic Value / Share = Equity Value / Diluted Shares
Upside / Downside = Intrinsic Value per Share / Current Price - 1
```

### Step 7: 三情景

| 情景 | 收入增长 | 利润率 | WACC | 终端增长/退出倍数 | 解释 |
|------|----------|--------|------|-------------------|------|
| Bear | 低于基准 | 利润率承压 | 较高 | 较低 | 核心风险兑现 |
| Base | 中性假设 | 稳态改善 | 中性 | 中性 | 管理层/行业中枢 |
| Bull | 高于基准 | 经营杠杆 | 较低 | 较高 | 催化剂兑现 |

### Step 8: 敏感性分析

标准 5×5，中心格 = Base case。常用组合：

- 行轴：WACC（Base ± 50/100 bps）
- 列轴：终端增长率（Base ± 25/50 bps）
- 或列轴：退出 EV/EBITDA 倍数

中心格必须等于 Base 每股内在价值。

## 输出模板

```markdown
📊 [公司] DCF 估值

结论: Base 内在价值 [X]/股，较当前价 [溢价/折价] [Y%]。

核心假设:
| 情景 | 收入 CAGR | EBIT Margin | WACC | Terminal g | 每股价值 |
|------|-----------|-------------|------|------------|----------|
| Bear | | | | | |
| Base | | | | | |
| Bull | | | | | |

价值桥接:
- 企业价值: ...
- 净债务/调整项: ...
- 股权价值: ...
- 稀释股本: ...
- 每股内在价值: ...

敏感性:
[5×5 表]

关键风险:
1. ...
2. ...
3. ...

以上仅供研究分析，不构成投资建议或交易指令。
```

## 参数边界

- 终端增长率：保守 2.0–2.5%，中性 2.5–3.5%，激进 3.5–5.0%；不得高于 WACC。
- CapEx/Revenue：轻资产 3–5%，中等 5–8%，重资产 8–15%。
- ΔNWC：通常为收入变化的 -2% 到 +2%；负值是现金来源，正值是现金使用。
- 周期行业：不要机械用低 PE/高利润率外推，Base 应回归周期中枢。
