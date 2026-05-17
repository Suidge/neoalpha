# Sector Overview — 行业概览

## 触发

"行业概览"、"sector overview"、"[板块] 分析"、"thematic research"、"行业深度"

## 定位

行业概览是 `Market Researcher` 主链的第一步：

```text
行业/主题定义 → Sector Overview → Competitive Landscape → Comps → Quantitative Screens → Thesis shortlist
```

输出必须服务于后续选股和 thesis，不做泛泛行业科普。

## 分析维度

1. **行业规模与增长**: 市场规模、CAGR、驱动因素
2. **行业结构**: 价值链、利润池、集中度、商业模式
3. **竞争格局**: 市场份额、进入壁垒、替代品威胁
3. **监管环境**: 政策趋势、合规要求
4. **技术趋势**: 颠覆性技术、数字化转型
5. **估值水平**: 行业平均 EV/EBITDA、P/E、P/S
6. **投资含义**: 最受益环节、潜在错定价、主要风险

## 数据获取

- 行业新闻：优先 `longbridge-news` 或 Longbridge topic/news。
- 行业规模：使用 web_search 搜索 `[sector] market size growth 2026`，优先行业协会、公司 IR、权威研究机构。
- 竞争格局：使用 web_search 搜索 `[sector] competitive landscape`。
- 估值水平：优先 Longbridge valuation/peer 数据；不足时搜索 `[sector] average EV/EBITDA P/E`，并标注来源。

## 工作流

### Step 1: Define Scope

| 字段 | 内容 |
|------|------|
| 行业/子行业 | 精确定义边界 |
| 研究目的 | 选股 / thesis / 持仓复核 / 主题跟踪 |
| 地域 | US / HK / A股 / Global |
| 公司宇宙 | 龙头、纯标的、二阶受益者、受损者 |
| 关键问题 | 本次研究要回答的 1-2 个判断 |

### Step 2: Market Overview

- TAM/SAM/SOM 分开写，避免把远期 TAM 当作可实现收入。
- 历史增长和未来增长分开，未来 CAGR 必须说明假设。
- 拆分需求驱动、价格驱动、政策驱动、技术驱动。

### Step 3: Industry Structure

| 维度 | 输出 |
|------|------|
| 价值链 | 上游/中游/下游/终端客户 |
| 利润池 | 哪一层毛利率最高，利润向哪里迁移 |
| 集中度 | CR3/CR5 或主要玩家份额 |
| 壁垒 | 技术、资本、客户认证、牌照、渠道 |
| 周期性 | 需求、库存、价格、产能周期 |

详细竞争格局进入 [competitive-landscape.md](competitive-landscape.md)。

### Step 4: Valuation Context

- 行业当前倍数 vs 历史区间。
- 高估值公司的溢价来源：增长、利润率、moat、稀缺性。
- 低估值公司的折价来源：周期、治理、债务、技术替代。

### Step 5: Investment Implications

必须输出：
1. 最值得研究的 3-5 个标的。
2. 每个标的表达的主题暴露。
3. 需要进入 Quantitative Screens 的指标。
4. 需要进入 thesis 的关键反证条件。

## 输出格式

```
📊 [行业] 概览

核心判断: [一句话]
行业规模: $XXB | CAGR: X% (2026-2030) | 数据日期: YYYY-MM-DD

价值链:
上游 → 中游 → 下游 → 终端客户
利润池: [...]

竞争格局:
• 龙头: [公司A] X% | [公司B] X% | [公司C] X%
• 进入壁垒: ...
• 替代品威胁: ...

监管环境: ...
技术趋势: ...

行业估值:
• 平均 EV/EBITDA: Xx | P/E: Xx | P/S: Xx

重点关注:
| 公司 | 市场 | 主题暴露 | 初步判断 | 下一步 |
|------|------|----------|----------|--------|
| | | | | Quantitative Screen / Competitive Landscape / Thesis |

以上仅供研究分析，不构成投资建议或交易指令。
```
