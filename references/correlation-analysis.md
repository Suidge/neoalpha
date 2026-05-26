# Correlation Analysis — 股票相关性分析

> **来源**: adapted from [himself65/finance-skills](https://github.com/himself65/finance-skills) stock-correlation skill
> **数据源**: Longbridge CLI k-line history → Python 计算
> **定位**: 补充投资系统的分析维度，用于持仓相关性管理、同涨同跌识别、配对交易候选

---

## 一、适用场景

| 场景 | 说明 |
|------|------|
| 持仓相关性管理 | 检查持仓组合中是否存在高相关性的标的，判断集中度风险 |
| 同涨同跌识别 | 某只股票异动时，快速找到可能被牵连的持仓/thesis 标的 |
| 配对交易候选 | 找到历史高相关的两只股票，观察是否出现价差偏离 |
| 板块联动验证 | 确认某标的与其所属板块/ETF 的跟踪程度 |
| 对冲选择 | 寻找与持仓负相关的标的，构建对冲 |

---

## 二、数据准备

### 2.1 从 Longbridge 获取日线数据

```python
import subprocess, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run(cmd, timeout=35):
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "").strip() if isinstance(e.stdout, str) else "", "timeout"

def fetch_kline(symbol, period="day", start="2025-05-17", end="2026-05-17"):
    """Fetch daily OHLCV for one symbol via Longbridge CLI."""
    code, out, err = run([
        "longbridge", "kline", "history", symbol,
        "--period", period, "--start", start, "--end", end, "--format", "json"
    ], timeout=30)
    if code != 0 or not out:
        return []
    try:
        data = json.loads(out)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def kline_to_close(kline_data):
    """Extract sorted close prices from kline data."""
    closes = []
    for row in kline_data:
        if isinstance(row, dict) and row.get("close"):
            closes.append(float(row["close"]))
    return closes  # already sorted chronologically from Longbridge
```

### 2.2 批量拉取

```python
SYMBOLS = ["AAPL.US", "MSFT.US", "GOOG.US", "AMZN.US", "META.US",
           "NVDA.US", "TSLA.US", "AMD.US", "INTC.US", "QCOM.US"]

closes = {}
for sym in SYMBOLS:
    data = fetch_kline(sym)
    closes[sym] = kline_to_close(data)
```

---

## 三、相关性计算

### 3.1 基础 Pearson 相关

```python
import numpy as np
import pandas as pd

def build_returns_matrix(closes_dict):
    """Build a DataFrame of daily log returns from close price dicts."""
    df = pd.DataFrame({sym: pd.Series(price) for sym, price in closes_dict.items()})
    returns = np.log(df / df.shift(1)).dropna()
    return returns

def correlation_matrix(returns):
    """Compute Pearson correlation matrix."""
    return returns.corr()

def correlation_to_target(target_symbol, corr_matrix):
    """Sort all correlations relative to a target symbol."""
    series = corr_matrix[target_symbol].drop(target_symbol).sort_values(ascending=False)
    return series
```

### 3.2 滚动相关性（时间变化）

```python
def rolling_correlation(returns, sym_a, sym_b, window=60):
    """Rolling Pearson correlation over a sliding window (default 60 trading days ~3mo)."""
    return returns[sym_a].rolling(window).corr(returns[sym_b])
```

### 3.3 同涨同跌检测

```python
def comovement_discovery(target_symbol, peer_symbols, returns, threshold=0.60):
    """Find which peers move most with the target."""
    corr = returns.corr()[target_symbol].drop(target_symbol)
    strong = corr[corr.abs() >= threshold].sort_values(ascending=False)
    return strong
```

### 3.4 对数收益 vs 简单收益

- **对数收益** `ln(P_t / P_{t-1})` — 更适合统计建模（正态性更好、时间可加）
- **简单收益** `(P_t - P_{t-1}) / P_{t-1}` — 更直观
- 本系统默认使用**对数收益**

---

## 四、同行筛选

### 4.1 从 Longbridge 获取同行列表

```python
def industry_peers(symbol):
    """Get industry peer group via Longbridge industry-peers command."""
    code, out, err = run([
        "longbridge", "industry-peers", symbol, "--format", "json"
    ], timeout=20)
    if code != 0 or not out:
        return []
    try:
        return json.loads(out)
    except Exception:
        return []
```

### 4.2 已知板块分组（fallback）

| 板块 | 标的 |
|------|------|
| Mag 7 | AAPL.US, MSFT.US, GOOG.US, AMZN.US, META.US, NVDA.US, TSLA.US |
| 半导体 | NVDA.US, AMD.US, INTC.US, QCOM.US, AVGO.US, MRVL.US, MU.US |
| 云计算 | MSFT.US, AMZN.US, GOOG.US, CRM.US, NOW.US, WDAY.US |
| 中概/恒科 | 700.HK, 9988.HK, 3690.HK, 1810.HK, 2228.HK, BABA.US, TCEHY.US |
| 大宗商品 | GLD.US, SLV.US, USO.US, XLE.US, FCX.US |
| 美债/利率 | TLT.US, UUP.US, TMF.US, SHY.US |

---

## 五、输出格式

### 相关性矩阵示例

```
         AAPL    MSFT    GOOG    AMZN    NVDA
AAPL    1.00    0.65    0.58    0.52    0.44
MSFT    0.65    1.00    0.62    0.55    0.48
GOOG    0.58    0.62    1.00    0.51    0.42
AMZN    0.52    0.55    0.51    1.00    0.39
NVDA    0.44    0.48    0.42    0.39    1.00
```

### 持仓相关性风险提示

```
组合相关性风险:
  AAPL vs MSFT = 0.65 (高 → 实质为科技仓位集中)
  NVDA vs AMD  = 0.82 (极高 → 同时持仓相当于单押半导体)
  建议: 考虑加入 TLT.US 或 GLD.US 降低组合相关性
```

---

## 六、集成到投资系统

### 6.1 盘前策略中的应用

在 `market_strategy_engine.py` 的 premarket pack 中增加 `correlation_context` 字段：

```python
def build_correlation_context(symbols):
    """Quick correlation check for thesis symbols vs each other."""
    if len(symbols) < 2:
        return {"note": "need ≥2 symbols for correlation"}
    closes_dict = {}
    for sym in symbols:
        data = fetch_kline(sym)
        closes_dict[sym] = kline_to_close(data)
    if len(closes_dict) < 2:
        return {"note": "insufficient data"}
    returns = build_returns_matrix(closes_dict)
    corr = correlation_matrix(returns)
    pairs = []
    for i, sym_a in enumerate(symbols):
        for sym_b in symbols[i+1:]:
            if sym_a in corr.index and sym_b in corr.columns:
                r = corr.loc[sym_a, sym_b]
                if abs(r) >= 0.60:
                    pairs.append({"pair": f"{sym_a} ↔ {sym_b}", "correlation": round(r, 3), "risk": "集中度风险" if r > 0.7 else "中等相关"})
    return {"pairs": pairs, "matrix_available": True}
```

### 6.2 调用入口

当用户问"XXX 和 YYY 的相关性"或"我的持仓相关性"时，优先使用本参考文档的分析框架，配合 Longbridge CLI 获取数据。

---

## 七、已知局限

1. **样本依赖**：较短时间窗口（<60 天）的相关性不可靠
2. **结构性变化**：公司基本面变化后历史相关性可能失效
3. **尾部相关性**：Pearson 相关系数在极端行情下可能低估共跌风险
4. **伪相关**：高相关≠因果关系，需结合基本面判断
