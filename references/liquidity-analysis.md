# Liquidity Analysis — 股票流动性分析

> **来源**: adapted from [himself65/finance-skills](https://github.com/himself65/finance-skills) stock-liquidity skill
> **数据源**: Longbridge CLI quote + kline history → Python 计算
> **定位**: 评估个股流动性和交易成本，辅助仓位规模决策

---

## 一、为什么流动性重要

流动性决定交易的真实成本。报价价格 ≠ 实际成交价。对于大额持仓（尤其港股/A 股中盘股），流动性不足可能导致：

- 建仓/平仓时产生显著滑点
- 止损时无法按目标价成交
- 大单进出推高交易成本
- 极端行情下流动性枯竭（无法平仓）

---

## 二、流动性维度

### 2.1 价差分析（Bid-Ask Spread）

```python
def spread_analysis(symbol):
    """Get current bid-ask spread from Longbridge quote."""
    code, out, err = run([
        "longbridge", "quote", symbol, "--format", "json"
    ], timeout=15)
    if code != 0 or not out:
        return None
    try:
        data = json.loads(out)
        row = data[0] if isinstance(data, list) else data
    except Exception:
        return None

    bid = float(row.get("bid_price") or 0)
    ask = float(row.get("ask_price") or 0)
    last = float(row.get("last_done") or row.get("last_price") or 0)

    if bid > 0 and ask > 0 and last > 0:
        spread = ask - bid
        spread_pct = (spread / ((ask + bid) / 2)) * 100
        return {
            "bid": bid,
            "ask": ask,
            "spread": round(spread, 4),
            "spread_pct": round(spread_pct, 4),
            "last_price": last,
            "spread_grade": "🟢 极好" if spread_pct < 0.05
            else "🟡 良好" if spread_pct < 0.15
            else "🟠 一般" if spread_pct < 0.50
            else "🔴 差"
        }
    return None
```

### 2.2 成交量分析

```python
def volume_analysis(symbol, lookback_days=60):
    """Analyze volume profile from kline history."""
    from datetime import datetime, timedelta
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    data = fetch_kline(symbol, start=start, end=end)
    if not data:
        return None

    volumes = [float(r["volume"]) for r in data if isinstance(r, dict) and r.get("volume")]
    closes = [float(r["close"]) for r in data if isinstance(r, dict) and r.get("close")]

    if not volumes:
        return None

    avg_vol = sum(volumes) / len(volumes)
    med_vol = sorted(volumes)[len(volumes)//2]
    avg_dollar_vol = sum(c * v for c, v in zip(closes, volumes)) / len(volumes)

    return {
        "avg_volume": round(avg_vol),
        "median_volume": round(med_vol),
        "avg_dollar_volume": round(avg_dollar_vol),
        "volume_cv": round(statistics.stdev(volumes) / avg_vol, 4) if len(volumes) > 1 else None,
        "trading_days": len(volumes),
    }
```

### 2.3 Amihud 非流动性指标

衡量价格对成交量的敏感度 — 越高表示流动性越差。

```python
def amihud_illiquidity(symbol, lookback_days=60):
    """Compute Amihud illiquidity ratio: average of |return| / dollar_volume."""
    from datetime import datetime, timedelta
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    data = fetch_kline(symbol, start=start, end=end)
    if not data or len(data) < 5:
        return None

    ratios = []
    for i in range(1, len(data)):
        r = data[i]
        prev = data[i-1]
        if not isinstance(r, dict) or not isinstance(prev, dict):
            continue
        ret = abs(float(r["close"]) / float(prev["close"]) - 1)
        dollar_vol = float(r["close"]) * float(r["volume"])
        if dollar_vol > 0:
            ratios.append(ret / dollar_vol)

    if not ratios:
        return None

    avg_illiq = sum(ratios) / len(ratios) * 1e6  # scale by 1e6 for readability
    return {
        "amihud_illiq": round(avg_illiq, 6),
        "grade": "🟢 极好" if avg_illiq < 0.001
        else "🟡 良好" if avg_illiq < 0.01
        else "🟠 一般" if avg_illiq < 0.1
        else "🔴 差"
    }
```

### 2.4 换手率分析

```python
def turnover_analysis(symbol):
    """Calculate turnover ratio: avg daily volume / float shares."""
    code, out, err = run([
        "longbridge", "calc-index", symbol, "--format", "json"
    ], timeout=15)
    if code != 0 or not out:
        return None
    try:
        data = json.loads(out)
    except Exception:
        return None

    # Longbridge calc-index may include turnover rate directly
    if isinstance(data, dict):
        turnover_rate = data.get("turnover_rate")
        if turnover_rate is not None:
            return {"turnover_rate": round(float(turnover_rate), 4), "source": "longbridge_direct"}
    return None
```

### 2.5 市场冲击估算

大额订单对价格的预估影响：

```python
def market_impact_estimate(symbol, order_value_usd):
    """Estimate market impact for a given order size using square-root model.
    impact ≈ σ * sqrt(order_value / total_dollar_volume)
    """
    from datetime import datetime, timedelta
    import math

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    data = fetch_kline(symbol, start=start, end=end)
    if not data:
        return None

    # Estimate daily volatility
    closes = [float(r["close"]) for r in data if isinstance(r, dict) and r.get("close")]
    returns = [(closes[i]/closes[i-1]-1) for i in range(1, len(closes))]
    daily_vol = statistics.stdev(returns) if len(returns) > 1 else 0.02

    # Avg dollar volume
    dollar_vols = [float(r["close"]) * float(r["volume"]) for r in data if isinstance(r, dict)]
    avg_dollar_vol = sum(dollar_vols) / len(dollar_vols) if dollar_vols else 1

    impact = daily_vol * math.sqrt(order_value_usd / avg_dollar_vol)
    return {
        "order_value_usd": order_value_usd,
        "avg_daily_dollar_volume": round(avg_dollar_vol),
        "daily_volatility": round(daily_vol, 4),
        "estimated_impact": round(impact * 100, 4),  # as %
        "grade": "🟢 可忽略" if impact < 0.002
        else "🟡 轻微" if impact < 0.01
        else "🟠 显著" if impact < 0.03
        else "🔴 严重"
    }
```

---

## 三、综合流动性评分

```python
def liquidity_score(symbol):
    """Compute a composite liquidity score (0-100)."""
    score = 50  # default neutral
    reasons = []

    spread = spread_analysis(symbol)
    if spread:
        sp = spread["spread_pct"]
        if sp < 0.05:
            score += 20
            reasons.append("极窄价差")
        elif sp < 0.15:
            score += 10
            reasons.append("良好价差")
        elif sp > 0.50:
            score -= 15
            reasons.append("宽价差")
        else:
            score -= 5
            reasons.append("价差一般")

    vol = volume_analysis(symbol)
    if vol:
        dv = vol["avg_dollar_volume"]
        if dv > 500_000_000:
            score += 15
            reasons.append(f"高日成交额 ${dv/1e9:.1f}B")
        elif dv > 50_000_000:
            score += 5
            reasons.append(f"中等成交额 ${dv/1e6:.0f}M")
        else:
            score -= 10
            reasons.append(f"低成交额 ${dv/1e6:.0f}M")

    illiq = amihud_illiquidity(symbol)
    if illiq:
        if illiq["grade"].startswith("🟢"):
            score += 10
        elif illiq["grade"].startswith("🔴"):
            score -= 15

    return {
        "symbol": symbol,
        "score": max(0, min(100, score)),
        "grade": "🟢 高流动性" if score >= 80
        else "🟡 良好" if score >= 60
        else "🟠 一般" if score >= 40
        else "🔴 低流动性",
        "reasons": reasons,
    }
```

---

## 四、流动性等级判定参考

| 等级 | 价差 (bps) | 日均成交额 | Amihud | 换手率 | 适合仓位 |
|------|-----------|-----------|--------|--------|---------|
| 🟢 极好 | <5 | >$5亿 | <0.001 | >1% | 大额无限制 |
| 🟡 良好 | 5-15 | $5000万-5亿 | <0.01 | 0.3-1% | 常规仓位 |
| 🟠 一般 | 15-50 | $1000-5000万 | <0.1 | 0.1-0.3% | 限制仓位≤5% |
| 🔴 差 | >50 | <$1000万 | >0.1 | <0.1% | 避免或极小仓位 |

---

## 五、集成到投资系统

### 5.1 盘前策略中的应用

在 `proactive_trader.py` 的 premarket pack 中增加 `liquidity_context` 字段：

```python
def build_liquidity_context(symbols):
    """Quick liquidity check for thesis/position symbols."""
    results = {}
    for sym in symbols[:20]:  # cap at 20 for speed
        try:
            results[sym] = liquidity_score(sym)
        except Exception:
            results[sym] = {"score": None, "grade": "数据不足"}
    return results
```

### 5.2 仓位规模决策

流动性不足时自动下调建议仓位比例：

```python
def max_position_pct(liquidity_grade):
    """Recommended max position % based on liquidity."""
    grades = {
        "🟢 高流动性": 0.25,   # 25%
        "🟡 良好": 0.15,       # 15%
        "🟠 一般": 0.05,       # 5%
        "🔴 低流动性": 0.02,   # 2%
    }
    return grades.get(liquidity_grade, 0.05)
```

---

## 六、已知局限

1. **快照 vs 日内变化**：价差分析基于快照，日内价差可能大幅波动
2. **香港市场特殊性**：港股流动性集中度高，小盘股流动性可能远低于表面数据
3. **事件驱动**：财报/分红/配股期间流动性可能骤变
4. **市场情绪**：恐慌/狂欢时流动性可能消失或异常放大
5. **数据频率限制**：Longbridge 日线数据无法提供盘内流动性变化