# Idea Generation — Quantitative Screens / 选股

> 来源参考：Anthropic `financial-services` equity-research `idea-generation`，已按个人投资系统、Longbridge 数据源和 SMAM 动量模型改写。

## 触发

"选股"、"screening"、"Quantitative Screens"、"stock ideas"、"投资机会"、"找标的"、"pitch me something"

## 一、先定义搜索边界

如果用户没有给出边界，先一次性确认：

| 参数 | 可选项 |
|------|--------|
| 方向 | Long / Short / Both / Watch |
| 市值 | Large / Mid / Small / Micro |
| 地域 | US / HK / A股 / Global |
| 行业 | 单一行业 / 跨行业 / 主题 |
| 风格 | Value / Growth / Quality / Momentum / Special Situation / Event-driven |
| 主题 | AI、能源、电力、半导体、医药、出海、重组等 |
| 期限 | 交易型(1-4周) / 中线(1-2季) / 长线(1年+) |

## 二、数据源优先级

1. Longbridge 系列：行情、估值、财务、同业、新闻、资金流、持仓。
2. thesis-tracker、portfolio/positions-current.json、watchlist、策略 YAML。
3. 公司 IR、公告、交易所、监管机构。
4. web_search 只补足行业规模、事件背景、海外可比和公开新闻。

所有数字必须写明来源和日期。无法验证的指标标记 `[UNVERIFIED]`，不能进入最终评分。

## 三、Quantitative Screens

筛选只生成候选，不生成结论。每个入选标的必须再进入 thesis、comps、DCF 或 catalyst 复核。

### 3.1 Value Screen

适用：低估值、均值回归、周期底部、价值修复。

| 指标 | 默认阈值 | 说明 |
|------|----------|------|
| P/E | 低于行业中位数 | 亏损公司改用 EV/Revenue、EV/GP |
| EV/EBITDA | 低于自身历史均值或同行中位数 | 周期行业必须用中周期 EBITDA |
| FCF yield | >5% | 现金流波动大时用 3 年平均 |
| P/B | <1.5x | 金融、资源、公用事业更适用 |
| 股息率 | 高于市场均值 | 检查派息可持续性 |
| Insider / Buyback | 90 天内内部人增持或回购 | 作为加分项，不单独构成买点 |

排除项：基本面恶化、债务压力、低估值来自盈利下修而非错杀。

### 3.2 Growth Screen

适用：收入扩张、利润弹性、成长股回调后再加速。

| 指标 | 默认阈值 | 说明 |
|------|----------|------|
| Revenue growth | >15% YoY | 高景气赛道可提高至 >25% |
| EPS / EBITDA growth | >20% YoY | 亏损转盈看 EBITDA margin 改善 |
| Revenue acceleration | 增速环比改善 | 连续 2 季更强 |
| Margin expansion | 毛利率或经营利润率提升 | 区分 mix 改善和一次性成本 |
| ROIC / ROE | >15% | 早期公司可用 gross margin + retention 替代 |
| SaaS retention | NDR >110% | 详见 `unit-economics.md` |

排除项：高增长但现金流恶化、获客成本失控、股权稀释过快。

### 3.3 Quality Screen

适用：核心持仓候选、长期配置、回撤中寻找高质量资产。

| 指标 | 默认阈值 | 说明 |
|------|----------|------|
| Revenue consistency | 5 年稳定增长或穿越周期 | 周期行业看销量/份额韧性 |
| Margin stability | 稳定或扩张 | 毛利率塌陷必须解释 |
| ROE / ROIC | >15% | 金融用 ROE，工业/科技优先 ROIC |
| Leverage | Debt/Equity 低或 Net Debt/EBITDA <2x | 利率敏感行业更严格 |
| FCF conversion | FCF / Net Income 高且稳定 | CapEx 重资产行业单独看 |
| Insider ownership | >5% 或管理层激励一致 | 国企/大盘股可不强求 |

排除项：利润质量差、应收/库存异常、治理风险、不可解释的关联交易。

### 3.4 Short / Avoid Screen

适用：做空候选、风险排除、持仓减仓预警。默认用于风险识别，不主动输出交易指令。

| 指标 | 红旗 |
|------|------|
| Revenue | 下滑或增速持续放缓 |
| Margin | 毛利率/经营利润率压缩 |
| Working capital | 应收账款或库存增速显著高于收入 |
| Valuation | 高于同行且缺乏增长/质量支撑 |
| Insider | 内部人大额减持 |
| Short interest | 高空头且基本面继续恶化 |
| Accounting | 审计师变更、重述、非经常项异常 |

若持仓触发两条以上红旗，必须回到 thesis 的逻辑破坏条件和 Battle Plan。

### 3.5 Special Situation Screen

适用：事件驱动、错杀修复、结构性变化。

| 类型 | 检查项 |
|------|--------|
| Recent IPO / SPAC | 锁定期到期、流通盘变化、业绩兑现 |
| Spin-off | 分拆后独立估值、被动卖压、管理层激励 |
| Restructuring | 债务重组、成本削减、亏损业务剥离 |
| Activist | 激进投资者介入、资本配置变化 |
| Management change | 新 CEO/CFO、战略转向、治理修复 |
| M&A / Regulatory | 交易审批、反垄断、关键许可证 |

Special situation 必须有明确时间窗口和可验证催化剂；没有催化剂的低估值通常只是价值陷阱。

## 四、SMAM 与综合评分

基本面 screen 决定“看什么”，SMAM 决定“什么时候看得更紧”。

| 模块 | 权重 | 说明 |
|------|------|------|
| Fundamental Fit | 35 | 对应 Value/Growth/Quality/Special Situation 得分 |
| Catalyst Quality | 20 | 催化剂强度、时间窗口、可验证性 |
| Valuation / Mispricing | 20 | 相对同行、自身历史、DCF/Comps 空间 |
| SMAM Momentum | 15 | CMS、Stability、VAM、VM_Score |
| Risk / Red Flags | -10 到 10 | Short screen 红旗扣分 |

评分解释：
- >80：进入深度 thesis / DCF
- 65-80：进入 watchlist，等待催化剂或回调
- 50-65：仅记录为主题线索
- <50：淘汰或标记 Avoid

### 4.1 Preset 选股器

当前已落地两个 preset：

| Preset | 用途 | 核心权重 |
|--------|------|----------|
| `short_term_momentum` | 短线 1-4 周观察 / 试仓候选 | 动量、题材、成交确认、催化剂 |
| `long_term_compounder` | 中长线 thesis / DCF 候选 | 基本面、产业面、竞争格局、估值空间 |

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --symbols TSEM.US,BABA.US --preset short_term_momentum
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --preset long_term_compounder --top 20
```

Preset 配置文件位于 `skills/neoalpha/presets/*.json`。脚本复用 SMAM 动量扫描结果，并结合 thesis-tracker 文本中的题材、催化剂、风险、基本面、竞争格局和估值线索做综合评分。

## 五、Thematic Sweep

主题筛选按以下顺序：

1. 定义主题论点：一句话说明为什么现在重要。
2. 画价值链：直接受益、间接受益、二阶受益、潜在受损。
3. 区分 pure-play 与 diversified exposure。
4. 检查哪些标的已被充分定价，哪些仍被低估。
5. 用 Quantitative Screens 过滤每一层候选。
6. 用 `competitive-landscape.md` 复核行业地位和 moat。
7. 输出 5-10 个候选，并标注下一步动作。

## 六、输出格式

```markdown
💡 选股候选 — [主题/行业/风格]

筛选边界: [方向 / 市值 / 地域 / 行业 / 风格 / 期限]
数据日期: [YYYY-MM-DD]

| Rank | 公司 | 市场 | Screen | P/E | EV/EBITDA | Rev YoY | ROE/ROIC | FCF Yield | CMS | 催化剂 | 综合评分 |
|------|------|------|--------|-----|-----------|---------|----------|-----------|-----|--------|----------|
| 1 | | | Growth+Quality | | | | | | | | |

Top Ideas:
1. [公司] — [Long/Watch/Short] — [一句话 thesis hook]
   - 为什么可能错定价:
   - 关键催化:
   - 主要风险/反证:
   - 下一步: thesis / comps / DCF / catalyst tracking

筛选方法:
- 使用的 screen:
- 数据源:
- 排除项:

以上仅供研究分析，不构成投资建议或交易指令。
```

## 七、复盘规则

- 每次 screen 结果保存候选和筛选条件，便于 30/60/90 天后复盘命中率。
- 命中率复盘字段：入选日价格、30/60/90 天收益、是否触发催化剂、screen 类型、失败原因。
- 若某类 screen 连续失效，调整阈值或降权，而不是继续机械使用。
