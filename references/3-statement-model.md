# 3-Statement Model — 三张表联动模型

> 参考 anthropics/financial-services (Apache 2.0)

## 触发

"三张表"、"3-statement"、"三表联动"、"IS BS CF"

## 概述

完整的 IS/BS/CF 联动填充框架。三张表是 DCF/LBO 的基础。

## 核心原则

1. **公式优先于硬编码** — 所有预测/联动单元格必须是公式
2. **分步验证** — IS → BS → CF，每步校验通过再继续
3. **三表联动** — BS 不平、CF 现金不轧差则模型有误

## 工作流（6 步）

### Step 1: 识别模板结构

列出所有 Tab 并映射：

| 常见 Tab 名 | 内容 |
|-------------|------|
| IS, P&L | 利润表 |
| BS, Balance Sheet | 资产负债表 |
| CF, CFS | 现金流量表 |
| Assumptions, Drivers | 假设驱动参数 |
| Checks, Validation | 校验表 |

→ 向用户确认 Tab 映射

### Step 2: 填入历史数据（3-5 年）

- IS: 营收 → COGS → 毛利润 → 费用 → EBITDA → D&A → EBIT → 利息 → 税前利润 → 税 → 净利润
- BS: 现金、AR、存货、PP&E、总资产、AP、短期债、长期债、权益
- CF: 经营/投资/融资现金流

**校验**: IS 净利润 = CF 经营现金流起点（间接法）
→ 向用户展示历史数据块，确认

### Step 3: 利润表预测

- 收入增长: 高增长 → 回归行业平均 → 终端
- 利润率: 毛利率、营业利润率、净利率趋势
- 费用: S&M/R&D/G&A 占收入比（规模效应下降）
- D&A: 占收入比或 CapEx 百分比
- 税率: 历史平均或法定税率

**校验**: 子项合计 = 总计
→ 向用户展示预测 IS，确认

### Step 4: 资产负债表

- AR = 收入 × DSO/365
- Inventory = COGS × DIO/365
- AP = COGS × DPO/365
- PP&E = 上期 + CapEx - D&A
- 债务 = 上期 - 当期还款
- 权益 = 上期 + 净利润 - 分红

**校验: 资产 = 负债 + 权益**（每期必须平衡）
→ 向用户展示 BS 及平衡校验，确认

### Step 5: 现金流量表

- CFO = 净利润 + D&A - ΔNWC
- CFI = -CapEx + 投资处置
- CFF = 债务变动 + 股权变动 - 分红

**校验: CF 期末现金 = BS 现金科目**
→ 向用户展示 CF 及现金轧差，确认

### Step 6: 最终校验

- 三表联动全部通过
- 公式引用正确
- 颜色标记正确（蓝色输入/黑色公式）

## Excel 规范

详见 [excel-conventions.md](excel-conventions.md)
