# SEPA Strategy — Minervini 趋势模板与动量选股框架

> **来源**: adapted from [himself65/finance-skills](https://github.com/himself65/finance-skills) sepa-strategy skill
> **理论基础**: Mark Minervini — *Trade Like a Stock Market Wizard*, *Mindset for Trading*
> **定位**: 与 SMAM 动量模型互补的选股/择时框架。SMAM 提供截面排名，SEPA 提供个股级别入场决策

---

## 一、核心哲学

**在正确的阶段、正确的时机买入正确的股票，严格风控。**

- 胜率约 50-55% — 盈利不来自高胜率，而来自**不对称盈亏比**（小亏大赚）
- 不预测市场，而是**对市场给出的信号做出响应**
- 专注于**成长股**（EPS/营收高增长），不适用价值股/周期股

---

## 二、阶段分析 (Stage Analysis)

每只股票经历四个阶段。**只允许在 Stage 2 买入。**

| 阶段 | 特征 | 操作 |
|------|------|------|
| **Stage 1 — 筑底** | 价格贴近200MA，MA走平/下降，MA缠绕，缩量 | 等待，不操作 |
| **Stage 2 — 上涨** | 更高高/低点，多头MA排列，上涨放量 | ✅ **唯一可买入阶段** |
| **Stage 3 — 见顶** | 高位宽幅震荡，假突破频繁，放量滞涨 | 减仓，不开新仓 |
| **Stage 4 — 下跌** | 跌破所有MA，空头排列，反弹即卖点 | 清仓，远离 |

### Base 计数（Stage 2 内部）

每次震荡-突破循环算一个 Base：
- **Base 1-2**: 最安全，上行空间最大 → 满仓
- **Base 3-4**: 仍有效但减仓 → 半仓
- **Base 5-6**: 晚期 → 最多1/4仓
- **Base 7+**: 回避（即将进入 Stage 3）

---

## 三、趋势模板 (Trend Template) — 8 项硬条件

**全部 8 项必须同时满足。** 任意一项不通过 = 不合格。

| # | 条件 | 含义 |
|---|------|------|
| 1 | 价格 > 150MA 且 价格 > 200MA | 中期趋势向上 |
| 2 | 150MA > 200MA | MA 多头排列 |
| 3 | 200MA 上涨 ≥ 1 个月（最好 4-5 个月） | 长期趋势确认 |
| 4 | 50MA > 150MA 且 50MA > 200MA | 短期MA排列正确 |
| 5 | 价格 > 50MA | 短期强势 |
| 6 | 价格 ≥ 52周低点 +30% | 脱离底部 |
| 7 | 价格在 52周高点 25% 以内 | 接近新高（不是抄底） |
| 8 | 相对强度 (RS) > 70 百分位（最好 85-90+） | 市场领涨股 |

### 记忆法

- **条件 1-5** = "MA 阶梯"（价格 > 50MA > 150MA > 200MA，200MA 上涨）
- **条件 6-7** = "价格位置"（远离低点，接近高点）
- **条件 8** = "相对强度"（市场领涨股）

---

## 四、基本面检查

强势基本面是区分真正领涨股和纯动量股的关键。

| 指标 | 门槛 | 说明 |
|------|------|------|
| 季度 EPS 增长 | ≥ 20%（最好 25-50%+） | <20% = 不合格 |
| EPS 加速度 | 当期 > 上期 | 减速即使正增长也是警告 |
| 年度 EPS 增长 | 连续 3 年 ≥ 25% | 长期成长性 |
| 营收增长 | 年 ≥ 15%，季 ≥ 20-25% | EPS 涨但营收不涨 = 成本削减（不可持续） |
| 利润率趋势 | 稳定或扩张 | 收缩即使 EPS 涨 = 红旗 |
| 机构持仓 | 增加中 | Smart money 进场 = 燃料 |
| 催化剂 | 新产品/FDA/大合同/市场扩张 | 有催化剂可涨 50-100%+，无则 15-25% |

### 基本面评级

| 等级 | 条件 | 含义 |
|------|------|------|
| 🅰 | EPS >30%，正增长，营收增长 | 最佳 |
| 🅱 | 15-30% | 良好 |
| 🅲 | 0-15% | 边缘 |
| 🅳 | 负增长 | 跳过 |

---

## 五、形态识别 — VCP (Volatility Contraction Pattern)

**SEPA 核心形态。** 在 Stage 2 的上升趋势中，寻找连续收缩的震荡区间。

### VCP 的 7 个特征

1. **必须是 Stage 2 趋势中**（先决条件）
2. **回调幅度递减**（如 20% → 12% → 6% → 3%），最少 3 次收缩，4-5 次理想
3. **成交量递减**，最后一次收缩出现"成交量枯竭"(VDU) — 多周最低量
4. **更高低点** — 每次回调底部高于前一次
5. **清晰的枢轴点** — 震荡区间上沿 = 突破阻力位
6. RS > 70（最好 85-90+）
7. 市场处于牛市或中性环境

### 其他有效形态

| 形态 | 回调深度 | 时长 | 特征 |
|------|---------|------|------|
| Cup with Handle | 杯 12-35%，柄 ≤12% | 7-65周 | U型底+小柄 |
| Flat Base | ≤15% | 5-10周 | 近期高位附近窄幅震荡 |
| Bull Flag | ≤旗杆 50% | 1-5周 | 急涨+窄幅回调 |
| High Tight Flag | ≤25%（在 100%+ 涨幅后） | 1-4周 | 最罕见但最强 |

---

## 六、与 SMAM 的互补关系

| 维度 | SMAM | SEPA |
|------|------|------|
| **视角** | 截面（跨标的排名） | 个股（时间序列形态） |
| **信号** | CMS 量化分数 | 趋势模板 8 条件 + VCP |
| **择时** | 动量分位决定加减仓 | 枢轴点突破决定入场 |
| **基本面** | VM_Score 含 PE 分位 | EPS/营收加速度+利润率 |
| **适用** | 持仓管理、批量筛选 | 新入场决策、仓位确认 |

### 联合使用流程

```
SMAM 扫描 → CMS Q1/Q2 标的 → SEPA 逐只检查趋势模板 → 符合则识别 VCP → 等待枢轴点突破 → 入场
         ↘ CMS Q4/Q5 → 不操作或减仓
```

---

## 七、Python 实现（Longbridge CLI 数据）

### 7.1 趋势模板检查

```python
def check_trend_template(symbol):
    """Check Minervini 8-condition trend template."""
    from datetime import datetime, timedelta

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    kline = fetch_kline(symbol, start=start, end=end)
    if not kline or len(kline) < 250:
        return {"error": "insufficient data (need ~250 trading days)"}

    closes = [float(r["close"]) for r in kline if isinstance(r, dict) and r.get("close")]

    # Compute MAs
    def ma(data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    price = closes[-1]
    ma50 = ma(closes, 50)
    ma150 = ma(closes, 150)
    ma200 = ma(closes, 200)

    # MA200 slope: compare current vs ~1 month ago (20 trading days)
    ma200_now = ma200
    ma200_1mo = ma(closes[:-20], 200) if len(closes) > 220 else None
    ma200_rising = ma200_now > ma200_1mo if ma200_1mo else None

    # 52-week high/low
    year_high = max(closes[-252:])
    year_low = min(closes[-252:])

    results = {
        "C1_price_above_150_200": price > ma150 and price > ma200 if ma150 and ma200 else None,
        "C2_150ma_above_200ma": ma150 > ma200 if ma150 and ma200 else None,
        "C3_200ma_rising": ma200_rising,
        "C4_50ma_above_150_200": ma50 > ma150 and ma50 > ma200 if ma50 and ma150 and ma200 else None,
        "C5_price_above_50ma": price > ma50 if ma50 else None,
        "C6_price_above_30pct_low": (price / year_low - 1) >= 0.30 if year_low else None,
        "C7_price_within_25pct_high": (year_high / price - 1) <= 0.25 if year_high else None,
        # C8 (RS) — would need market-wide ranking data
    }

    conditions_passed = sum(1 for v in results.values() if v is True)
    conditions_total = sum(1 for v in results.values() if v is not None)
    results["passed"] = f"{conditions_passed}/{conditions_total}"
    results["all_passed"] = conditions_passed == conditions_total

    return results
```

### 7.2 VCP 检测

```python
def detect_vcp(closes, highs, lows, volumes):
    """Detect VCP pattern from price/volume data (last 60-120 days)."""
    # This requires intraday high/low data for drawdown calculation
    # Simple approximation: check recent pullback sequence
    if len(closes) < 60:
        return {"detected": False, "reason": "insufficient data"}

    # Find local peaks and troughs
    peaks = []
    troughs = []
    for i in range(5, len(closes) - 5):
        if closes[i] > closes[i-1] and closes[i] > closes[i-2] and closes[i] > closes[i-3] and closes[i] > closes[i+1]:
            peaks.append((i, closes[i]))
        if closes[i] < closes[i-1] and closes[i] < closes[i-2] and closes[i] < closes[i+1]:
            troughs.append((i, closes[i]))

    # Need at least 3 pullback cycles
    if len(peaks) < 3:
        return {"detected": False, "reason": "too few peaks for VCP"}

    # Check decreasing drawdown depth
    drawdowns = []
    for p_idx in range(min(len(peaks)-1, 4)):
        peak_price = peaks[p_idx][1]
        # Find nearest trough after this peak
        next_trough = min([t for t in troughs if t[0] > peaks[p_idx][0]],
                          key=lambda x: x[0], default=None)
        if next_trough:
            dd = (peak_price - next_trough[1]) / peak_price * 100
            drawdowns.append(dd)

    if len(drawdowns) >= 3:
        decreasing = all(drawdowns[i] > drawdowns[i+1] for i in range(len(drawdowns)-1))
        return {
            "detected": decreasing,
            "drawdowns": [round(d, 1) for d in drawdowns],
            "pattern": "VCP detected" if decreasing else "drawdowns not contracting",
        }
    return {"detected": False, "reason": "need 3+ pullbacks"}
```

---

## 八、交易设置清单

入场前逐项检查：

1. **趋势模板**: 8 项全部通过？
2. **阶段**: Stage 2？Base 计数？
3. **基本面**: EPS/营收/利润率评级 ≥ B？
4. **形态**: VCP 或其他有效形态？
5. **枢轴点**: 清晰的突破价位？
6. **成交量**: 突破日放量（≥ 日均量 1.5x）？
7. **RS**: 相对强度 > 70？
8. **市场环境**: 大盘趋势向上/横盘？
9. **盈亏比**: 目标收益 ≥ 止损距离 3x？
10. **仓位**: 根据 Base 计数和流动性确定仓位比例？

---

## 九、已知局限

1. **数据要求高**：需要 ~250 个交易日的完整日线数据，港股部分小盘股数据不足
2. **A 股适用性**：涨跌停限制 + T+1 结算 → VCP 突破后无法及时止损
3. **震荡市失效**：横盘阶段趋势模板频繁切换通过/不通过
4. **主观性**：VCP 形态识别有一定主观成分，自动化检测精度有限
5. **RS 数据**：截面相对强度排名需全市场数据，Longbridge 目前不直接提供