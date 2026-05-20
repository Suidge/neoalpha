# Earnings Integration — 财报分析整合流程

> **自动化脚本**: `scripts/analyze_earnings_preview.py`（财报前瞻）和 `scripts/analyze_earnings_recap.py`（财报复盘）
> 优先使用脚本获取结构化数据，再结合本框架进行人工分析

## Phase 0: 自动化数据获取

### 财报前瞻
```bash
python3 skills/investment-system/scripts/analyze_earnings_preview.py <SYMBOL> --output text
```
返回结构化数据：一致预期、EPS 预测、近期财务、估值、财报日历

### 财报复盘
```bash
python3 skills/investment-system/scripts/analyze_earnings_recap.py <SYMBOL> --output text
```
返回结构化数据：实际 vs 预期、营收/利润趋势、毛利率趋势、价格反应

### 数据源优先级
1. `analyze_earnings_preview.py` / `analyze_earnings_recap.py`（Longbridge CLI 自动化）
2. Longbridge 直接命令（`consensus`、`forecast-eps`、`financial-report`）
3. web_search 补充（call transcript、管理层指引细节）

---

## Phase 1: 数据收集清单

### 必须获取的数据
1. **财报核心数字**（优先 `longbridge-earnings` / Longbridge CLI；web_search 仅补充）：
   - 营收（实际 vs 预期）
   - EPS（实际 vs 预期）
   - 关键运营指标（MAU、GMV、ARR 等，视行业而定）
   - 下季度/全年指引

2. **股价反应**：
   - 先读取 `longbridge-quote` / `longbridge-kline` 规则。
   - 复杂命令先运行 `longbridge quote --help`、`longbridge kline --help` 或 `longbridge kline history --help`。
   - 获取当前价格与财报前后日 K，标注数据时间。

3. **管理层要点**（Longbridge filing/news 优先；web_search 搜索 earnings call transcript/highlights 作为补充）：
   - 关键引用
   - 指引变化
   - 战略更新

## Phase 2: 分析框架

### Beat/Miss 判定标准
- **显著 Beat**: >3% 营收 Beat 或 >5% EPS Beat
- **轻微 Beat**: 1-3% 营收 Beat 或 2-5% EPS Beat
- **符合预期**: ±1% 以内
- **轻微 Miss**: 1-3% 营收 Miss 或 2-5% EPS Miss
- **显著 Miss**: >3% 营收 Miss 或 >5% EPS Miss

### 利润率分析要点
- 毛利率变化：成本压力还是定价权？
- 营业利润率：运营杠杆还是成本失控？
- 自由现金流：盈利质量如何？

### 指引分析
- 上调 = 管理层信心增强
- 下调 = 谨慎或基本面恶化
- 维持 = 中性，结合上下文判断

## Phase 3: 输出检查清单

- [ ] 所有数字已通过 longbridge 或 web_search 验证
- [ ] Beat/Miss 判断有明确量化依据
- [ ] 给出了明确的"我们的判断"
- [ ] 区分了事实（数据）和观点（解读）
- [ ] 没有使用训练数据中的旧财报
- [ ] 标注了财报发布日期
- [ ] 涉及目标价/交易动作时已加入“不构成投资建议或交易指令”声明
