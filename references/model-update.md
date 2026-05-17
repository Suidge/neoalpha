# Model Update — 模型增量更新

## 触发

"更新模型"、"model update"、"新数据进来"、"刷新 DCF"、"刷新估值"

## 场景

已有 DCF/Comps/LBO/3-Statement 模型，新财报或新数据发布后**增量更新**而非从头重建。

## 工作流

### Step 1: 识别变更范围

先判断触发类型：

| 触发 | 例子 | 重点 |
|------|------|------|
| Earnings release | 新季度 actuals | actual vs prior estimate vs consensus |
| Guidance change | 公司上调/下调全年指引 | 新旧指引差异 |
| Assumption revision | 行业价格、销量、利润率变化 | 哪个 driver 被改 |
| Macro update | 利率、汇率、商品价格 | WACC、成本、需求 |
| Event-driven | M&A、重组、新产品、监管 | 是否改变核心矛盾 |

明确：
- 哪些历史数据需要追加？
- 哪些假设需要更新？
- 哪些公式应自动联动？
- 哪些输出会受影响？

### Step 2: 更新输入层

- 替换历史数据块中的新值
- 更新假设驱动参数（增长率、利润率、WACC 输入等）
- **不要改公式**，只改输入
- 每个新增输入写来源、日期、口径；无法验证标记 `[UNVERIFIED]`

### Step 2b: Actual vs Estimate / Consensus

| Line Item | Prior Estimate | Consensus | Actual | Delta vs Prior | Delta vs Consensus | Source |
|-----------|----------------|-----------|--------|----------------|--------------------|--------|
| Revenue | | | | | | |
| Gross Margin | | | | | | |
| EBITDA / EBIT | | | | | | |
| EPS | | | | | | |
| FCF | | | | | | |
| Key KPI | | | | | | |

Segment detail 如可得，必须拆分到业务线；否则说明缺失原因。

### Step 3: 验证联动

- 检查预测是否自动更新
- 检查三张表是否仍然平衡
- 检查敏感性表格中心格 = 基准值
- 运行或引用 [model-audit.md](model-audit.md)；若有 Critical，先修模型再解释结论

### Step 4: 估值影响

| Valuation Method | Prior | Updated | Change | Driver |
|------------------|-------|---------|--------|--------|
| DCF fair value | | | | |
| P/E implied value | | | | |
| EV/EBITDA implied value | | | | |
| Comps percentile | | | | |
| Price target / Base value | | | | |

必须说明变化来自：actuals、forward estimates、WACC、terminal assumptions、multiple、share count、net debt。

### Step 5: 变更摘要

```
📝 模型更新摘要 — [公司]

更新内容:
• 新增 FY2025 历史数据
• 更新收入增长假设: X% → Y%
• 更新 WACC: X% → Y%

Actual vs Estimate:
• Revenue: actual X vs prior Y / consensus Z
• EPS: actual X vs prior Y / consensus Z

影响:
• 每股内在价值: $XX → $YY
• 相对当前股价: [溢价/折价] X%
• Thesis impact: Strengthen / Neutral / Weaken

无需修改:
• 终值假设、资本结构假设
```

## 原则

- **只更新输入，不改公式** — 如公式需要改说明原模型设计有问题
- **每次更新记录版本** — 标注日期和变更内容
- **校验优先** — 先跑校验再输出结果
- **信号和噪音分开** — 一次性项目、会计调整、季节性因素不得直接外推
- **估值变化必须可追溯** — 说明变化来自哪个 driver
