# Earnings Preview — 财报前瞻

> 用于财报发布前的情景分析，与 earnings-workflow（财报后分析）互补
> **自动化脚本**: `scripts/analyze_earnings_preview.py` — 一键获取结构化数据

## 触发

"财报前瞻 [公司]"、"pre-earnings [公司]"、"[公司] QX 前瞻"

## 工作流

### Step 0: 自动化数据获取（优先）

```bash
python3 skills/investment-system/scripts/analyze_earnings_preview.py <SYMBOL> --output text
```

脚本自动获取：一致预期、EPS 预测、近期财务、估值、财报日历。
获取后进入 Step 2 进行情景分析。

### Step 1: 收集上下文（脚本数据不足时补充）

1. 确认公司及报告季度
2. 获取一致预期：优先 `longbridge-earnings-preview` / Longbridge consensus；不足时使用 web_search 搜索 `[Company] QX 2026 consensus estimates`
3. 确认财报日期和时间（盘前/盘后）
4. 回顾上季度电话会中的指引

### Step 2: 关键指标框架

**通用指标**：
- 营收 vs 一致预期（总计 + 分部）
- EPS vs 一致预期
- 利润率趋势
- 自由现金流
- 前瞻指引 vs 一致预期

**行业特有指标**：
| 行业 | 关键指标 |
|------|----------|
| 科技/SaaS | ARR、净留存率、RPO、客户数 |
| 零售 | 同店销售、客流、客单价 |
| 工业 | 在手订单、Book-to-Bill |
| 金融 | NIM、信贷质量、贷款增长 |
| 医疗 | 处方量、患者数、管线更新 |

### Step 3: 情景分析

| 情景 | 营收 | EPS | 关键驱动 | 股价反应 |
|------|------|-----|----------|----------|
| Bull | | | | |
| Base | | | | |
| Bear | | | | |

### Step 4: 催化剂清单

列出 3-5 个将决定股价反应的关键因素

### Step 5: 输出格式

```
🔮 [公司] Q[X] 财报前瞻

财报日: [日期] [盘前/盘后]
一致预期: 营收 $XX | EPS $XX

关键指标（按重要性排序）:
1. ...

情景分析:
• Bull: ...
• Base: ...
• Bear: ...

催化剂:
1. ...

交易设置: 期权隐含波动 ±X% | 历史财报波动 ±X%

以上仅供研究分析，不构成投资建议或交易指令。
```
