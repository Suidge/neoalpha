# Data Layer — 数据接口与降级规则

## 原则

1. **Longbridge 优先**：股票、行情、估值、新闻、财务数据先用 Longbridge CLI 或对应 sibling skill。
2. **先查当前命令格式**：CLI 会变化；复杂子命令先运行 `longbridge <subcommand> --help`。
3. **web_search 只补缺口**：用于宏观数据、电话会 transcript、公司 IR 页面、行业报告、未被 Longbridge 收录的事件。
4. **web_fetch 只读指定 URL**：不是搜索工具；拿到 IR / filing / transcript URL 后再读取。
5. **来源落地**：输出关键数字时标注来源、日期和口径；口径不一致时不强行合并。

## 数据映射

| 需要的数据 | 首选入口 | sibling skill | web fallback |
|------------|----------|---------------|--------------|
| 当前价格、涨跌、成交量 | `longbridge quote` | `longbridge-quote` | 交易所/公司 IR 页面 |
| K 线 / 财报前后走势 | `longbridge kline history` | `longbridge-kline` | Yahoo/交易所历史行情 |
| 新闻、公告、社区情绪 | `longbridge news`, `longbridge filing`, `longbridge topic` | `longbridge-news` | 公司 IR、SEC/HKEX、主流新闻 |
| 财务报表 / KPI | `longbridge financial-report`, `financial-statement` | `longbridge-fundamental` | 年报/季报 PDF 或 IR 数据表 |
| 一致预期 / EPS 修订 | `longbridge consensus`, `forecast-eps` | `longbridge-earnings-preview` | analyst consensus 搜索结果 |
| 估值倍数 / 历史分位 | `longbridge valuation`, `valuation-rank`, `industry-valuation` | `longbridge-valuation` | 可靠金融数据页 |
| 同业对比 | Longbridge peer/company data | `longbridge-peer-comparison` | 公司列表 + 逐项验证 |
| 市场情绪 | `longbridge market-temp <MARKET>` | `longbridge-market-temp` | 主要指数/宏观新闻 |
| 持仓与账户 | `longbridge positions`, `portfolio` | `longbridge-positions`, `longbridge-portfolio` | 无；不可用时说明缺数据 |

## 使用 web_search 的写法

不要把 `web_search query=...` 写进 shell 代码块。应写成：

- 使用 web_search 搜索：`[Company] Q1 2026 earnings call transcript`
- 使用 web_search 搜索：`10 year treasury yield today`
- 使用 web_search 搜索：`[sector] market size CAGR 2026`

## 质量检查

- [ ] 每个关键数字都有来源和日期
- [ ] 实时价格/估值未使用训练数据
- [ ] CLI 参数已通过 help 或 sibling skill 确认
- [ ] web_search 结果只用于补充，不覆盖 Longbridge 已验证数据
- [ ] 口径冲突时明确说明，不给虚假的精确结论
