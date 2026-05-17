# Model Audit — 模型审计与错误排查

> 来源参考：Anthropic `financial-services` audit-xls，已适配本系统 DCF、LBO、3-statement、Comps 和 headless xlsx 工具链。

## 触发

"审计模型"、"model audit"、"debug model"、"模型不平"、"检查公式"、"QA spreadsheet"、"DCF 校验"、"三表不平"

## 一、审计范围

| 范围 | 使用场景 |
|------|----------|
| Selection | 只检查用户指定区域或关键输出区域 |
| Sheet | 检查单个 sheet 的公式、引用、单位和格式 |
| Model | DCF、LBO、3-statement、Comps 等完整模型 |

默认：生成或更新估值模型后，至少做 `Model` 级审计。

## 二、通用公式检查

| 检查项 | 典型问题 |
|--------|----------|
| Formula errors | `#REF!`、`#VALUE!`、`#N/A`、`#DIV/0!`、`#NAME?` |
| Hardcodes inside formulas | `=A1*1.05`，其中 `1.05` 应来自假设单元格 |
| Inconsistent formulas | 同行/同列公式模式断裂 |
| Off-by-one ranges | `SUM`/`AVERAGE` 漏掉首行或尾行 |
| Pasted-over formulas | 应为公式的单元格被硬编码覆盖 |
| Broken links | 跨 sheet 引用断裂或指向错误 |
| Unit mismatch | 千元/百万元/实际值混用，百分比口径混乱 |
| Hidden rows/sheets | 隐藏区域含旧假设、override 或废弃计算 |

## 三、模型结构检查

| 检查项 | 标准 |
|--------|------|
| 输入/公式分离 | 输入区、计算区、输出区清晰 |
| 颜色规范 | 蓝色输入、黑色公式、绿色外部链接，或遵循模板自身规则 |
| Tab flow | Assumptions → Historical → Forecast → Valuation → Output → Checks |
| 日期表头 | 历史/预测期间一致 |
| 来源记录 | 每个外部输入有来源、日期、口径 |

## 四、三表联动检查

### Balance Sheet

| 检查 | 测试 |
|------|------|
| BS balances | Total Assets = Total Liabilities + Equity |
| Retained earnings | Prior RE + Net Income - Dividends = Current RE |
| Debt rollforward | Opening debt + new debt - repayment = ending debt |

BS 不平时，先量化每期差额，再追溯资产、负债、权益三块；不要继续解释估值。

### Cash Flow

| 检查 | 测试 |
|------|------|
| Cash tie-out | CF ending cash = BS cash |
| CFO + CFI + CFF | 合计等于现金变化 |
| D&A match | CF D&A = IS D&A |
| CapEx match | CF CapEx 与 PP&E rollforward 一致 |
| NWC sign | AR、Inventory、AP 的现金流方向正确 |

### Income Statement

| 检查 | 测试 |
|------|------|
| Revenue build | 分部收入合计 = 总收入 |
| Tax | 税费与税前利润/税率匹配 |
| Share count | EPS 使用稀释股本，股本变动有来源 |

## 五、模型类型专项检查

### DCF

- FCF 使用 unlevered 口径，不能扣 interest expense。
- WACC 使用市场价值权重，不使用账面价值权重。
- Terminal value 已折现回估值日。
- Terminal growth `g < WACC`，且不高于长期名义经济增速。
- Terminal value 占 EV >75% 时标黄，要求解释。
- 敏感性表中心格必须等于 Base case。

### LBO

- Sources & Uses 平衡。
- Debt paydown 与 cash sweep 机制一致。
- PIK interest 正确滚入本金。
- Exit multiple 使用正确 EBITDA 口径（LTM/NTM）。
- Management rollover、交易费用、融资费用进入 Day 1 equity bridge。
- IRR/MOIC 对 interim distribution 或 dividend recap 有处理。

### 3-Statement

- Working capital 方向正确。
- D&A 与 PP&E schedule 一致。
- 债务到期表与本金偿还一致。
- 现金不能无约束变负；如为 plug，必须标注。

### Comps

- Peer set 与行业/规模/增长/地域/商业模式匹配。
- EV、净债务、市值、少数股东权益口径一致。
- 亏损公司不用 P/E 作为核心倍数。
- 极端值单列并说明是否剔除。
- 平均值和中位数都给出；优先解释中位数。

## 六、审计输出

```markdown
## Model Audit — [公司/模型]

模型类型: DCF / LBO / 3-statement / Comps / Custom
整体结论: Clean / Minor Issues / Major Issues
Critical: X | Warning: Y | Info: Z

| # | Sheet | Cell/Range | Severity | Category | Issue | Suggested Fix |
|---|-------|------------|----------|----------|-------|---------------|
| 1 | | | Critical | BS balance | | |

关键校验:
- BS balance:
- Cash tie-out:
- Sensitivity center:
- Hardcodes:
- Source coverage:

下一步:
1. [必须先修的项]
2. [可后续优化项]
```

## 七、修复规则

- 默认只报告，不直接改模型。
- 若用户要求修复，先修 Critical，再修 Warning。
- 改公式前备份文件或生成新版本。
- 每次修复后重新运行 audit，直到 Critical = 0。
