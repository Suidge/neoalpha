#!/usr/bin/env python3
"""Medium-term market health scan for premarket strategy packs.

Read-only data source: Longbridge K-line CLI. The scan is a risk backdrop,
not a trading signal by itself.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple


MARKET_INDEXES = {
    "US": [
        {"symbol": ".SPX.US", "name": "标普500指数", "role": "primary"},
        {"symbol": ".IXIC.US", "name": "纳斯达克综合指数", "role": "growth"},
        {"symbol": ".DJI.US", "name": "道琼斯工业指数", "role": "blue_chip"},
        {"symbol": "QQQ.US", "name": "纳斯达克100 ETF", "role": "growth_etf"},
        {"symbol": "SPY.US", "name": "标普500 ETF", "role": "broad_etf"},
        {"symbol": "IWM.US", "name": "罗素2000 ETF", "role": "small_cap"},
        {"symbol": "SOXX.US", "name": "半导体 ETF", "role": "sector_leadership"},
    ],
    "HK": [
        {"symbol": "HSI.HK", "name": "恒生指数", "role": "primary"},
        {"symbol": "HSTECH.HK", "name": "恒生科技指数", "role": "growth"},
        {"symbol": "HSCEI.HK", "name": "恒生中国企业指数", "role": "china_h_share"},
        {"symbol": "000001.SH", "name": "上证指数", "role": "a_share_broad"},
        {"symbol": "399001.SZ", "name": "深证成指", "role": "a_share_growth"},
        {"symbol": "399006.SZ", "name": "创业板指", "role": "a_share_growth"},
        {"symbol": "000300.SH", "name": "沪深300", "role": "a_share_large_cap"},
    ],
}

MA_PERIODS = (5, 10, 20, 60, 120, 250)


def run_longbridge(args: Sequence[str], timeout: int = 45) -> Any:
    proc = subprocess.run(
        ["longbridge", *args, "--format", "json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")
    return json.loads(proc.stdout)


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def round_opt(value: Optional[float], digits: int = 3) -> Optional[float]:
    return round(value, digits) if value is not None else None


def moving_average(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(value * alpha + out[-1] * (1 - alpha))
    return out


def macd(values: List[float]) -> Dict[str, Optional[float]]:
    if len(values) < 35:
        return {"dif": None, "dea": None, "hist": None, "above_zero": None}
    fast = ema_series(values, 12)
    slow = ema_series(values, 26)
    dif_series = [f - s for f, s in zip(fast, slow)]
    dea_series = ema_series(dif_series, 9)
    dif = dif_series[-1]
    dea = dea_series[-1]
    return {
        "dif": round_opt(dif, 4),
        "dea": round_opt(dea, 4),
        "hist": round_opt((dif - dea) * 2, 4),
        "above_zero": bool(dif > 0 and dea > 0),
    }


def weekly_closes(candles: List[Dict[str, Any]]) -> List[float]:
    weeks: Dict[str, float] = {}
    for row in candles:
        close = to_float(row.get("close"))
        ts = str(row.get("time") or "")
        if close is None or len(ts) < 10:
            continue
        # Calendar week grouping is sufficient for a regime filter.
        from datetime import date

        d = date.fromisoformat(ts[:10])
        year, week, _ = d.isocalendar()
        weeks[f"{year}-{week:02d}"] = close
    return list(weeks.values())


def consecutive_below(values: List[float], level: Optional[float]) -> int:
    if level is None:
        return 0
    count = 0
    for value in reversed(values):
        if value < level:
            count += 1
        else:
            break
    return count


def slope_pct(values: List[float], period: int, lookback: int = 5) -> Optional[float]:
    if len(values) < period + lookback:
        return None
    now = moving_average(values, period)
    past = sum(values[-period - lookback : -lookback]) / period
    if now is None or not past:
        return None
    return (now / past - 1) * 100


def recent_swing(candles: List[Dict[str, Any]], lookback: int = 80) -> Dict[str, Any]:
    window = candles[-lookback:] if len(candles) > lookback else candles
    highs = [(to_float(r.get("high")), r.get("time")) for r in window]
    lows = [(to_float(r.get("low")), r.get("time")) for r in window]
    highs = [(v, t) for v, t in highs if v is not None]
    lows = [(v, t) for v, t in lows if v is not None]
    if not highs or not lows:
        return {}
    high, high_time = max(highs, key=lambda x: x[0])
    low, low_time = min(lows, key=lambda x: x[0])
    midpoint = low + (high - low) * 0.5
    return {
        "lookback_days": len(window),
        "swing_high": round_opt(high),
        "swing_high_time": high_time,
        "swing_low": round_opt(low),
        "swing_low_time": low_time,
        "half_retracement": round_opt(midpoint),
    }


def key_bearish_candle(candles: List[Dict[str, Any]], lookback: int = 20) -> Optional[Dict[str, Any]]:
    candidates = []
    for row in candles[-lookback:]:
        open_ = to_float(row.get("open"))
        close = to_float(row.get("close"))
        high = to_float(row.get("high"))
        low = to_float(row.get("low"))
        if open_ is None or close is None or high is None or low is None or not open_:
            continue
        drop = (close / open_ - 1) * 100
        range_pct = (high / low - 1) * 100 if low else 0
        if drop <= -1.2 and range_pct >= 1.5:
            candidates.append((drop, row))
    if not candidates:
        return None
    _, row = min(candidates, key=lambda x: x[0])
    return {
        "time": row.get("time"),
        "open": round_opt(to_float(row.get("open"))),
        "high": round_opt(to_float(row.get("high"))),
        "low": round_opt(to_float(row.get("low"))),
        "close": round_opt(to_float(row.get("close"))),
    }


def box_range(candles: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, Optional[float]]:
    window = candles[-lookback:] if len(candles) > lookback else candles
    highs = [to_float(r.get("high")) for r in window]
    lows = [to_float(r.get("low")) for r in window]
    highs = [v for v in highs if v is not None]
    lows = [v for v in lows if v is not None]
    return {
        "lookback_days": len(window),
        "high": round_opt(max(highs) if highs else None),
        "low": round_opt(min(lows) if lows else None),
    }


def health_score(
    close: float,
    ma: Dict[str, Optional[float]],
    ma20_slope: Optional[float],
    days_below_ma20: int,
    daily_macd: Dict[str, Optional[float]],
    weekly_macd: Dict[str, Optional[float]],
    swing: Dict[str, Any],
) -> Tuple[int, List[str], List[str]]:
    positives: List[str] = []
    negatives: List[str] = []
    score = 0

    ma20 = ma.get("ma20")
    ma60 = ma.get("ma60")
    ma120 = ma.get("ma120")
    ma250 = ma.get("ma250")
    if ma20 is not None and close >= ma20:
        score += 2
        positives.append("收盘在20日线上方")
    elif ma20 is not None:
        score -= 2
        negatives.append("收盘跌破20日线")
        if days_below_ma20 >= 3:
            score -= 1
            negatives.append("连续3天以上未收复20日线")

    if ma20_slope is not None and ma20_slope > 0:
        score += 1
        positives.append("20日线仍向上")
    elif ma20_slope is not None:
        score -= 1
        negatives.append("20日线拐头向下")

    if ma60 is not None and ma120 is not None and close >= ma60 and ma60 >= ma120:
        score += 1
        positives.append("60/120日中期结构未破")
    elif ma60 is not None and close < ma60:
        score -= 1
        negatives.append("跌破60日线")

    if ma60 is not None and ma120 is not None and ma250 is not None and ma60 >= ma120 >= ma250:
        score += 1
        positives.append("60/120/250日均线维持多头排列")

    if daily_macd.get("above_zero"):
        score += 1
        positives.append("日线MACD在零轴上方")
    else:
        score -= 1
        negatives.append("日线MACD未站上零轴")

    if weekly_macd.get("above_zero"):
        score += 1
        positives.append("周线MACD在零轴上方")
    else:
        score -= 1
        negatives.append("周线MACD未站上零轴")

    half = to_float(swing.get("half_retracement"))
    if half is not None and close >= half:
        score += 1
        positives.append("未跌破本轮波段50%回撤位")
    elif half is not None:
        score -= 2
        negatives.append("跌破本轮波段50%回撤位")

    return score, positives, negatives


def status_from_score(score: int) -> str:
    if score >= 4:
        return "healthy"
    if score >= 0:
        return "warning"
    return "damaged"


def fetch_candles(symbol: str, count: int = 280) -> List[Dict[str, Any]]:
    data = run_longbridge(["kline", symbol, "--period", "day", "--count", str(count)], timeout=60)
    if isinstance(data, dict):
        rows = data.get("data") or data.get("candles") or []
    else:
        rows = data
    return [r for r in rows if isinstance(r, dict) and to_float(r.get("close")) is not None]


def scan_symbol(item: Dict[str, str]) -> Dict[str, Any]:
    symbol = item["symbol"]
    candles = fetch_candles(symbol)
    closes = [to_float(r.get("close")) for r in candles]
    closes = [v for v in closes if v is not None]
    if len(closes) < 60:
        return {"symbol": symbol, "name": item["name"], "role": item["role"], "status": "unavailable", "error": "insufficient_kline"}

    close = closes[-1]
    ma = {f"ma{p}": round_opt(moving_average(closes, p)) for p in MA_PERIODS}
    ma20_slope = slope_pct(closes, 20, 5)
    daily_macd = macd(closes)
    weekly_macd = macd(weekly_closes(candles))
    swing = recent_swing(candles)
    bearish = key_bearish_candle(candles)
    box = box_range(candles)
    days_below = consecutive_below(closes, ma.get("ma20"))
    score, positives, negatives = health_score(close, ma, ma20_slope, days_below, daily_macd, weekly_macd, swing)
    status = status_from_score(score)

    key_reclaim_levels = []
    if ma.get("ma20") is not None and close < ma["ma20"]:
        key_reclaim_levels.append({"level": ma["ma20"], "type": "ma20", "reason": "收复20日线"})
    if bearish:
        key_reclaim_levels.append({"level": bearish["high"], "type": "bearish_candle_high", "reason": "收复最近标志性阴线高点"})

    invalidation_levels = []
    if swing.get("half_retracement") is not None:
        invalidation_levels.append({"level": swing["half_retracement"], "type": "half_retracement", "reason": "跌破本轮波段50%回撤位"})
    if ma.get("ma60") is not None:
        invalidation_levels.append({"level": ma["ma60"], "type": "ma60", "reason": "跌破60日线"})
    if box.get("low") is not None:
        invalidation_levels.append({"level": box["low"], "type": "box_low_20d", "reason": "跌破20日整理区间低点"})

    return {
        "symbol": symbol,
        "name": item["name"],
        "role": item["role"],
        "status": status,
        "score": score,
        "last_close": round_opt(close),
        "last_time": candles[-1].get("time"),
        "ma": ma,
        "ma20_slope_5d_pct": round_opt(ma20_slope),
        "days_below_ma20": days_below,
        "daily_macd": daily_macd,
        "weekly_macd": weekly_macd,
        "swing": swing,
        "key_bearish_candle": bearish,
        "box_range_20d": box,
        "key_reclaim_levels": key_reclaim_levels,
        "invalidation_levels": invalidation_levels,
        "positive_evidence": positives[:5],
        "negative_evidence": negatives[:5],
    }


def aggregate_status(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [r for r in results if r.get("status") in {"healthy", "warning", "damaged"}]
    if not valid:
        return {
            "status": "unavailable",
            "risk_level": "unknown",
            "strategy_bias": "insufficient_data",
            "summary": "Longbridge K-line data unavailable for the selected benchmarks.",
        }
    damaged = [r for r in valid if r["status"] == "damaged"]
    warning = [r for r in valid if r["status"] == "warning"]
    primary = [r for r in valid if r.get("role") in {"primary", "growth"}]
    primary_damaged = [r for r in primary if r["status"] == "damaged"]

    if primary_damaged or len(damaged) >= max(2, len(valid) // 3):
        status, risk, bias = "damaged", "high", "风控优先，降低追高和新增风险暴露"
    elif warning or damaged:
        status, risk, bias = "warning", "medium", "持有为主，等待20日线/关键阴线高点收复再提高进攻性"
    else:
        status, risk, bias = "healthy", "low", "允许按计划参与强势方向，但仍需观察扩散质量"

    failed = [r for r in valid if r["status"] in {"warning", "damaged"}]
    leaders = [r for r in valid if r["status"] == "healthy"]
    return {
        "status": status,
        "risk_level": risk,
        "strategy_bias": bias,
        "failed_indices": [{"symbol": r["symbol"], "name": r["name"], "status": r["status"], "score": r["score"]} for r in failed],
        "healthy_indices": [{"symbol": r["symbol"], "name": r["name"], "score": r["score"]} for r in leaders[:4]],
        "summary": f"{len(leaders)}/{len(valid)} 个核心观察对象健康，{len(warning)} 个警戒，{len(damaged)} 个受损。",
    }


def scan_market_health(market: str) -> Dict[str, Any]:
    market = market.upper()
    if market not in MARKET_INDEXES:
        raise ValueError("market must be US or HK")
    results: List[Dict[str, Any]] = []
    for item in MARKET_INDEXES[market]:
        try:
            results.append(scan_symbol(item))
        except Exception as exc:
            results.append({
                "symbol": item["symbol"],
                "name": item["name"],
                "role": item["role"],
                "status": "unavailable",
                "error": str(exc)[:160],
            })
    aggregate = aggregate_status(results)
    return {
        "schema_version": 1,
        "market": market,
        "framework": "medium_term_market_health",
        "source": "longbridge kline day OHLCV",
        "purpose": "Premarket risk backdrop for market_watch; do not use as a standalone trade signal.",
        "indicators": ["MA5/10/20/60/120/250", "20MA reclaim within 3 sessions", "daily/weekly MACD zero-axis", "50% swing retracement", "recent bearish candle high", "20-day box range"],
        **aggregate,
        "indices": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan medium-term market health from Longbridge K-line data.")
    parser.add_argument("--market", choices=["US", "HK"], required=True)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()
    data = scan_market_health(args.market)
    print(json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))


if __name__ == "__main__":
    main()
