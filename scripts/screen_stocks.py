#!/usr/bin/env python3
"""Preset stock screener for NeoAlpha.

The screener keeps the existing universe inputs and layers preset scoring on
top of SMAM momentum results plus thesis-tracker text signals.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "neoalpha"
PRESETS_DIR = SKILL / "presets"
DEFAULT_THESIS_DIR = Path.home() / "Documents" / "neoalpha" / "thesis-tracker"
THESIS_DIR = Path(os.environ.get("INVESTMENT_THESIS_DIR", str(DEFAULT_THESIS_DIR))).expanduser()
MOMENTUM_SCANNER = SKILL / "scripts" / "screen_momentum.py"
TZ = timezone(timedelta(hours=8))
TECH_CACHE_DIR = Path(os.environ.get("NEOALPHA_TECH_CACHE_DIR", "~/.cache/neoalpha/kline")).expanduser()
DEFAULT_TECH_CACHE_HOURS = float(os.environ.get("NEOALPHA_TECH_CACHE_HOURS", "6"))
DEFAULT_KLINE_DELAY = float(os.environ.get("NEOALPHA_KLINE_DELAY", "0.2"))
DEFAULT_DAILY_BARS = int(os.environ.get("NEOALPHA_DAILY_BARS", "380"))

CATALYST_KEYWORDS = [
    "催化",
    "订单",
    "合同",
    "指引",
    "财报",
    "政策",
    "并购",
    "重组",
    "合作",
    "扩产",
    "产能",
    "预付款",
    "回购",
    "增持",
    "approval",
    "contract",
    "guidance",
    "earnings",
    "buyback",
]

RISK_KEYWORDS = [
    "风险",
    "减持",
    "下修",
    "负债",
    "现金流恶化",
    "毛利率压缩",
    "竞争加剧",
    "监管",
    "地缘",
    "诉讼",
    "稀释",
    "overhang",
    "dilution",
    "lawsuit",
]

FUNDAMENTAL_KEYWORDS = [
    "营收",
    "收入",
    "增速",
    "净利润",
    "EPS",
    "毛利率",
    "利润率",
    "ROE",
    "ROIC",
    "FCF",
    "现金流",
    "负债",
    "margin",
    "revenue",
    "earnings",
]

INDUSTRY_KEYWORDS = [
    "产业链",
    "赛道",
    "TAM",
    "渗透率",
    "供需",
    "周期",
    "政策",
    "技术路线",
    "市场空间",
    "行业景气",
    "value chain",
]

COMPETITIVE_KEYWORDS = [
    "竞争",
    "护城河",
    "壁垒",
    "份额",
    "定价权",
    "客户粘性",
    "成本优势",
    "先发优势",
    "moat",
    "market share",
    "pricing power",
]

VALUATION_KEYWORDS = [
    "估值",
    "低估",
    "上行空间",
    "目标价",
    "DCF",
    "PE",
    "EV/EBITDA",
    "EV/Sales",
    "Forward",
    "upside",
    "target",
]


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def word_score(text: str, keywords: list[str], full_at: int) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    hits = 0
    for keyword in keywords:
        if keyword.lower() in lower:
            hits += 1
    return clamp(hits / max(1, full_at) * 100)


def load_preset(name_or_path: str) -> dict[str, Any]:
    path = Path(name_or_path)
    if not path.exists():
        path = PRESETS_DIR / f"{name_or_path}.json"
    if not path.exists():
        raise SystemExit(f"Preset not found: {name_or_path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_thesis_symbols(thesis_dir: Path = THESIS_DIR) -> list[str]:
    if not thesis_dir.is_dir():
        return []
    symbols = []
    for path in thesis_dir.iterdir():
        symbol = thesis_symbol_from_path(path)
        if symbol:
            symbols.append(symbol)
    return sorted(symbols)


def thesis_symbol_from_path(path: Path) -> str:
    if path.suffix != ".md":
        return ""
    match = re.match(r"^([A-Za-z0-9]+)\.(US|HK|SH|SZ)(?:-.+)?$", path.stem)
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}".upper()


def thesis_path(symbol: str, thesis_dir: Path = THESIS_DIR) -> Path | None:
    exact = thesis_dir / f"{symbol}.md"
    if exact.exists():
        return exact
    code, market = symbol.rsplit(".", 1)
    matches = sorted(thesis_dir.glob(f"{code}.{market}-*.md"))
    return matches[0] if matches else None


def thesis_text(symbol: str, thesis_dir: Path = THESIS_DIR) -> str:
    path = thesis_path(symbol, thesis_dir)
    if not path:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def run_momentum_scan(symbols: list[str]) -> dict[str, Any]:
    cmd = [
        "python3",
        str(MOMENTUM_SCANNER),
        "--symbols",
        ",".join(symbols),
        "--with-value",
        "--json",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(90, len(symbols) * 35),
        )
        if result.returncode != 0:
            raise SystemExit(result.stderr.strip() or result.stdout.strip() or "momentum scan failed")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired as e:
        print(f"[WARN] Momentum scan timed out after {e.timeout}s, falling back to empty scan", file=sys.stderr)
        return {"results": []}
    except Exception as e:
        print(f"[WARN] Momentum scan failed: {e}, falling back to empty scan", file=sys.stderr)
        return {"results": []}


def parse_pe_rank(pe_rank: str | None) -> tuple[int, int]:
    if not pe_rank:
        return (0, 0)
    match = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", str(pe_rank))
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def momentum_score(row: dict[str, Any]) -> float:
    cms = float(row.get("cms") or 0)
    stability = float(row.get("stability") or 0)
    vam = float(row.get("vam") or 0)
    mom_12_1 = float((row.get("signals") or {}).get("MOM_12_1") or 0)
    cms_part = clamp((cms + 0.25) / 1.50 * 100)
    stability_part = clamp(stability * 100)
    vam_part = clamp((vam + 0.25) / 1.50 * 100)
    mom_part = clamp((mom_12_1 + 0.10) / 0.60 * 100)
    return 0.45 * cms_part + 0.25 * stability_part + 0.20 * vam_part + 0.10 * mom_part


def liquidity_volume_score(row: dict[str, Any]) -> float:
    ratio = float(row.get("volume_ratio") or 1)
    return clamp((ratio - 0.8) / 0.9 * 100)


def valuation_score(row: dict[str, Any], text: str) -> float:
    vm_score = row.get("vm_score")
    vm_part = clamp((float(vm_score or 0) + 1.0) / 2.0 * 100)
    pe_rank, pe_total = parse_pe_rank(row.get("pe_rank"))
    if pe_total:
        pe_part = clamp((1 - pe_rank / pe_total) * 100)
        quantitative = 0.55 * vm_part + 0.45 * pe_part
    else:
        quantitative = vm_part
    qualitative = word_score(text, VALUATION_KEYWORDS, full_at=4)
    return 0.65 * quantitative + 0.35 * qualitative


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _rolling(values: list[float], window: int, fn) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(fn(values[i + 1 - window : i + 1]))
    return out


def _ma(values: list[float], window: int) -> list[float | None]:
    return _rolling(values, window, lambda xs: sum(xs) / len(xs))


def _ema(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def _tdx_sma(values: list[float], period: int, weight: int = 1) -> list[float]:
    if not values:
        return []
    out = [values[0]]
    for value in values[1:]:
        out.append((weight * value + (period - weight) * out[-1]) / period)
    return out


def _latest(values: list[Any], offset: int = 0) -> Any:
    idx = len(values) - 1 - offset
    if idx < 0:
        return None
    return values[idx]


def _is_rising(values: list[float | None], lookback: int = 1, tolerance: float = 0.0) -> bool:
    current = _latest(values)
    previous = _latest(values, lookback)
    return current is not None and previous is not None and current >= previous * (1 + tolerance)


def _every_rising(values: list[float | None], lookback: int, tolerance: float = -0.001) -> bool:
    clean = [v for v in values if v is not None]
    if len(clean) < lookback + 1:
        return False
    tail = clean[-lookback - 1 :]
    return all(tail[i] >= tail[i - 1] * (1 + tolerance) for i in range(1, len(tail)))


def _count(condition: list[bool], lookback: int) -> int:
    return sum(1 for item in condition[-lookback:] if item)


def _hhv(values: list[float], lookback: int, offset: int = 0) -> float:
    end = len(values) - offset
    start = max(0, end - lookback)
    return max(values[start:end]) if end > start else 0.0


def _llv(values: list[float], lookback: int, offset: int = 0) -> float:
    end = len(values) - offset
    start = max(0, end - lookback)
    return min(values[start:end]) if end > start else 0.0


def _bars_since_highest(values: list[float], lookback: int) -> int:
    tail = values[-lookback:]
    if not tail:
        return 0
    high = max(tail)
    return len(tail) - 1 - max(i for i, value in enumerate(tail) if value == high)


def _crossed_up(a: list[float], b: list[float], offset: int = 0) -> bool:
    return (
        _latest(a, offset) is not None
        and _latest(b, offset) is not None
        and _latest(a, offset + 1) is not None
        and _latest(b, offset + 1) is not None
        and _latest(a, offset) > _latest(b, offset)
        and _latest(a, offset + 1) <= _latest(b, offset + 1)
    )


def _normalize_kline_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("data", "items", "candles", "klines", "list"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return []
    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        close = _to_float(item.get("close") or item.get("c"), None)
        high = _to_float(item.get("high") or item.get("h"), None)
        low = _to_float(item.get("low") or item.get("l"), None)
        open_ = _to_float(item.get("open") or item.get("o"), None)
        volume = _to_float(item.get("volume") or item.get("vol") or item.get("v"), 0.0)
        if close is None or high is None or low is None or open_ is None:
            continue
        rows.append({"open": open_, "high": high, "low": low, "close": close, "volume": volume})
    return rows


def fetch_daily_klines(
    symbol: str,
    bars: int = DEFAULT_DAILY_BARS,
    cache_hours: float = DEFAULT_TECH_CACHE_HOURS,
    delay: float = DEFAULT_KLINE_DELAY,
) -> list[dict[str, Any]]:
    TECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = TECH_CACHE_DIR / f"{symbol.replace('/', '_')}-day-{bars}.json"
    if cache_hours > 0 and cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours <= cache_hours:
            try:
                return _normalize_kline_items(json.loads(cache_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

    cmd = ["longbridge", "kline", symbol, "--period", "day", "--count", str(bars), "--adjust", "forward", "--format", "json"]
    last_error = ""
    for attempt in range(3):
        result = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if result.returncode == 0:
            cache_path.write_text(result.stdout, encoding="utf-8")
            if delay > 0:
                time.sleep(delay)
            return _normalize_kline_items(json.loads(result.stdout))
        last_error = result.stderr.strip() or result.stdout.strip()
        if "429002" in last_error or "limited" in last_error.lower():
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    print(f"[WARN] daily kline failed for {symbol}: {last_error[:160]}", file=sys.stderr)
    return []


def _technical_inputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [_to_float(r["close"]) for r in rows]
    highs = [_to_float(r["high"]) for r in rows]
    lows = [_to_float(r["low"]) for r in rows]
    opens = [_to_float(r["open"]) for r in rows]
    volumes = [_to_float(r["volume"]) for r in rows]
    white = _ema(_ema(closes, 10), 10)
    yellow = []
    ma14, ma28, ma57, ma114 = _ma(closes, 14), _ma(closes, 28), _ma(closes, 57), _ma(closes, 114)
    for vals in zip(ma14, ma28, ma57, ma114):
        yellow.append(sum(vals) / 4 if all(v is not None for v in vals) else None)
    bbi = []
    ma3, ma6, ma12, ma24 = _ma(closes, 3), _ma(closes, 6), _ma(closes, 12), _ma(closes, 24)
    for vals in zip(ma3, ma6, ma12, ma24):
        bbi.append(sum(vals) / 4 if all(v is not None for v in vals) else None)
    ema144, ema169, ema288, ema338 = _ema(closes, 144), _ema(closes, 169), _ema(closes, 288), _ema(closes, 338)

    dif = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26))]
    dea = _ema(dif, 9)
    macd = [(a - b) * 2 for a, b in zip(dif, dea)]

    rsv9 = []
    for i, close in enumerate(closes):
        low9 = min(lows[max(0, i - 8) : i + 1])
        high9 = max(highs[max(0, i - 8) : i + 1])
        rsv9.append(50.0 if high9 == low9 else 100 * (close - low9) / (high9 - low9))
    k = _tdx_sma(rsv9, 3, 1)
    d = _tdx_sma(k, 3, 1)
    j = [3 * kk - 2 * dd for kk, dd in zip(k, d)]

    lc = [closes[i - 1] if i > 0 else closes[i] for i in range(len(closes))]
    gains = [max(c - prev, 0) for c, prev in zip(closes, lc)]
    ranges = [abs(c - prev) for c, prev in zip(closes, lc)]
    rsi3_denom = _tdx_sma(ranges, 3, 1)
    rsi3 = [(num / den * 100) if den else 50.0 for num, den in zip(_tdx_sma(gains, 3, 1), rsi3_denom)]

    short = []
    long = []
    for i, close in enumerate(closes):
        low3 = min(lows[max(0, i - 2) : i + 1])
        high3 = max(closes[max(0, i - 2) : i + 1])
        low21 = min(lows[max(0, i - 20) : i + 1])
        high21 = max(closes[max(0, i - 20) : i + 1])
        short.append(50.0 if high3 == low3 else 100 * (close - low3) / (high3 - low3))
        long.append(50.0 if high21 == low21 else 100 * (close - low21) / (high21 - low21))

    var1a = []
    var3a = []
    for i, close in enumerate(closes):
        high4 = max(highs[max(0, i - 3) : i + 1])
        low4 = min(lows[max(0, i - 3) : i + 1])
        var1a.append((high4 - close) / (high4 - low4) * 100 - 90 if high4 != low4 else -40)
        var3a.append((close - low4) / (high4 - low4) * 100 if high4 != low4 else 50)
    var2a = [x + 100 for x in _tdx_sma(var1a, 4, 1)]
    var4a = _tdx_sma(var3a, 6, 1)
    var5a = [x + 100 for x in _tdx_sma(var4a, 6, 1)]
    brick = [max(v5 - v2 - 4, 0) for v5, v2 in zip(var5a, var2a)]

    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "white": white,
        "yellow": yellow,
        "bbi": bbi,
        "ema144": ema144,
        "ema169": ema169,
        "ema288": ema288,
        "ema338": ema338,
        "dif": dif,
        "dea": dea,
        "macd": macd,
        "j": j,
        "k": k,
        "rsi3": rsi3,
        "short": short,
        "long": long,
        "brick": brick,
    }


def technical_factors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) < 120:
        return {"available": False, "reason": f"insufficient daily bars: {len(rows)}"}
    data = _technical_inputs(rows)
    c, o, h, l, v = data["close"], data["open"], data["high"], data["low"], data["volume"]
    white, yellow, bbi = data["white"], data["yellow"], data["bbi"]
    j, rsi3, short, long = data["j"], data["rsi3"], data["short"], data["long"]
    close, open_, high, low, volume = c[-1], o[-1], h[-1], l[-1], v[-1]
    prev_close = c[-2] if len(c) > 1 else close
    amplitude = (high - low) / low * 100 if low else 0
    change_abs = abs(close - prev_close) / prev_close * 100 if prev_close else 0
    is_up_doji = close > prev_close and abs(close - open_) / open_ * 100 < 1.8 if open_ else False
    white_now = _latest(white)
    yellow_now = _latest(yellow)
    bbi_now = _latest(bbi)
    trend_ok = bool(white_now and yellow_now and white_now >= yellow_now * 0.999 and (close >= yellow_now * 0.997 or close > open_))
    strong_trend = bool(
        trend_ok
        and _every_rising(yellow, 13)
        and _every_rising(white, 11, tolerance=0.0)
        and all((ww or 0) > (yy or 10**9) for ww, yy in list(zip(white, yellow))[-20:])
    )
    recent_range = (_hhv(h, 20) - _llv(l, 20)) / _llv(l, 20) * 100 if _llv(l, 20) else 0
    far_range = (_hhv(h, 50) - _llv(l, 50)) / _llv(l, 50) * 100 if _llv(l, 50) else 0
    single_needle = (short[-1] <= 20 and long[-1] >= 75) or (long[-1] - short[-1] >= 70)
    washout = _count([(ss <= 20 and ll >= 75) or (ll - ss >= 70) for ss, ll in zip(short, long)], 10) >= 2
    vday = _bars_since_highest(v, 40)
    big_green = vday < len(c) and c[-1 - vday] < c[-2 - vday] and c[-1 - vday] < o[-1 - vday] if len(c) > vday + 1 else False
    big_green_ok = (not big_green) or vday >= 15
    shrink = volume < _hhv(v, 20) * 0.416 or volume < _hhv(v, 50) / 3
    pullback_shrink = volume < _hhv(v, 20) * 0.45 or volume < _hhv(v, 50) / 3
    super_shrink = volume < _hhv(v, 30) / 4 or volume < _hhv(v, 50) / 6
    active_range = recent_range >= 15 or far_range >= 30 or washout
    white_dist = abs(close - white_now) / close * 100 if white_now and close else 100
    low_white_dist = abs(low - white_now) / white_now * 100 if white_now else 100
    bbi_dist = abs(close - bbi_now) / close * 100 if bbi_now and close else 100
    low_bbi_dist = abs(low - bbi_now) / bbi_now * 100 if bbi_now else 100
    yellow_dist = abs(close - yellow_now) / yellow_now * 100 if yellow_now else 100
    pullback_white = (
        (white_now and close >= white_now and white_dist <= 2)
        or (white_now and close < white_now and white_dist < 0.8)
        or (bbi_now and close >= bbi_now and bbi_dist < 2.5 and low_bbi_dist < 1 and white_dist <= 3 and change_abs < 1 and close > prev_close)
    )
    pullback_yellow = (
        (yellow_now and close >= yellow_now and (yellow_dist <= 1.5 or (yellow_dist <= 2 and change_abs < 1)))
        or (yellow_now and close < yellow_now and yellow_dist <= 0.8)
    )
    oversold_turn = trend_ok and (rsi3[-1] - 15) >= rsi3[-2] and (rsi3[-2] < 20 or j[-2] < 14)
    oversold_shrink = trend_ok and (j[-1] < 14 or rsi3[-1] < 23) and (rsi3[-1] + j[-1] < 55 or j[-1] == min(j[-20:]))
    original_b1 = bool(
        white_now and yellow_now and white_now > yellow_now and close >= yellow_now * 0.99
        and _is_rising(yellow)
        and (j[-1] < 13 or rsi3[-1] < 21)
        and rsi3[-1] + j[-1] < min((a + b) for a, b in zip(rsi3[-15:], j[-15:])) * 1.5
    )
    pullback_b1 = strong_trend and (j[-1] < 30 or rsi3[-1] < 40 or washout) and rsi3[-1] + j[-1] < 70 and pullback_white
    yellow_b1 = trend_ok and (j[-1] < 13 or rsi3[-1] < 18) and pullback_yellow and _is_rising(_ma(c, 60), tolerance=0.0)
    b1_hits = {
        "oversold_turn": oversold_turn and amplitude < 5.5 and (change_abs < 2.3 or (is_up_doji and change_abs < 4)) and big_green_ok and active_range,
        "oversold_shrink": oversold_shrink and amplitude < 5 and (change_abs < 2.5 or is_up_doji) and big_green_ok and shrink and active_range,
        "original_b1": original_b1 and big_green_ok and active_range and (shrink or super_shrink or white_dist < 1.8 or bbi_dist < 1.5 or yellow_dist < 2.8),
        "super_shrink": trend_ok and (j[-1] < 14 or rsi3[-1] < 23) and rsi3[-1] + j[-1] < 60 and far_range >= 45 and super_shrink and big_green_ok and active_range,
        "pullback_white": pullback_b1 and amplitude < 5.5 and (change_abs < 2 or (change_abs < 5 and white_dist < 1.5)) and big_green_ok and pullback_shrink and active_range,
        "pullback_yellow": yellow_b1 and big_green_ok and (shrink or super_shrink) and recent_range >= 11.9 and far_range >= 19.5,
    }
    b1_score = clamp(sum(22 if hit else 0 for hit in b1_hits.values()) + (12 if washout else 0))
    needle_score = clamp((45 if single_needle else 0) + (25 if trend_ok else 0) + (15 if shrink or super_shrink else 0) + (15 if active_range else 0))
    macd_crosses = [_crossed_up(data["dif"], data["dea"], offset=i) for i in range(min(21, len(c) - 1))]
    recent_cross = any(macd_crosses[:5])
    zero_up = data["dif"][-1] > 0 and data["dea"][-1] > 0
    zero_down = data["dif"][-1] < 0 and data["dea"][-1] < 0
    macd_score = clamp((45 if recent_cross else 0) + (35 if zero_up and data["dif"][-1] > data["dea"][-1] else 0) + (15 if zero_down and recent_cross else 0) + (10 if data["macd"][-1] > data["macd"][-2] else 0))
    brick = data["brick"]
    strong_red = len(brick) >= 3 and brick[-1] > brick[-2] and brick[-2] <= brick[-3]
    kinetic = (j[-1] - j[-2] + rsi3[-1] - rsi3[-2]) / 2
    upper_shadow_ok = close >= open_ or close > prev_close
    if high > min(low, prev_close):
        upper_shadow_ok = upper_shadow_ok and (1 - (high - close) / (high - min(low, prev_close))) > 0.618
    impulse_score = clamp((45 if strong_red else 0) + (25 if kinetic >= 8 else 0) + (15 if any(b1_hits.values()) or (long[-2] > 85 and short[-2] < 30) else 0) + (15 if trend_ok and upper_shadow_ok else 0))
    trend_score = clamp(
        (25 if trend_ok else 0)
        + (15 if _is_rising(white) else 0)
        + (15 if _every_rising(yellow, 13) else 0)
        + (15 if close > data["ema144"][-1] and close > data["ema169"][-1] else 0)
        + (15 if close > data["ema288"][-1] and close > data["ema338"][-1] else 0)
        + (15 if recent_range >= 10 or far_range >= 25 else 0)
    )
    accumulation_score = clamp(
        (25 if trend_ok else 0)
        + (20 if strong_trend else 0)
        + (20 if white_dist <= 6 or yellow_dist <= 8 else 0)
        + (15 if not big_green else 0)
        + (10 if _every_rising(bbi, 20) else 0)
        + (10 if far_range >= 30 else 0)
    )
    return {
        "available": True,
        "close": round(close, 4),
        "trend_regime": round(trend_score, 1),
        "pullback_setup": round(b1_score, 1),
        "single_needle_washout": round(needle_score, 1),
        "macd_phase_confirmation": round(macd_score, 1),
        "impulse_confirmation": round(impulse_score, 1),
        "technical_regime": round(trend_score, 1),
        "accumulation_quality": round(accumulation_score, 1),
        "signals": {
            "trend_ok": trend_ok,
            "strong_trend": strong_trend,
            "shrink": shrink,
            "super_shrink": super_shrink,
            "active_range": active_range,
            "single_needle": single_needle,
            "recent_macd_cross": recent_cross,
            "macd_above_zero": zero_up,
            "strong_brick_turn": strong_red,
            "b1_hits": b1_hits,
            "white_distance_pct": round(white_dist, 2),
            "yellow_distance_pct": round(yellow_dist, 2),
            "amplitude_pct": round(amplitude, 2),
            "recent_range_pct": round(recent_range, 2),
            "far_range_pct": round(far_range, 2),
            "j": round(j[-1], 2),
            "rsi3": round(rsi3[-1], 2),
            "short": round(short[-1], 2),
            "long": round(long[-1], 2),
        },
    }


def load_technical_map(
    symbols: list[str],
    bars: int = DEFAULT_DAILY_BARS,
    cache_hours: float = DEFAULT_TECH_CACHE_HOURS,
    delay: float = DEFAULT_KLINE_DELAY,
) -> dict[str, dict[str, Any]]:
    tech = {}
    for symbol in symbols:
        rows = fetch_daily_klines(symbol, bars=bars, cache_hours=cache_hours, delay=delay)
        tech[symbol] = technical_factors(rows)
    return tech


def component_score(name: str, row: dict[str, Any], text: str, preset: dict[str, Any]) -> float:
    if name == "momentum":
        return momentum_score(row)
    if name == "concept_strength":
        concepts = preset.get("concept_keywords") or []
        return word_score(text, list(concepts), full_at=3)
    if name == "liquidity_volume":
        return liquidity_volume_score(row)
    if name == "catalyst":
        return word_score(text, CATALYST_KEYWORDS, full_at=4)
    if name == "risk_penalty":
        return word_score(text, RISK_KEYWORDS, full_at=4)
    if name == "fundamental_quality":
        return word_score(text, FUNDAMENTAL_KEYWORDS, full_at=7)
    if name == "industry_structure":
        return word_score(text, INDUSTRY_KEYWORDS, full_at=4)
    if name == "competitive_position":
        return word_score(text, COMPETITIVE_KEYWORDS, full_at=4)
    if name == "valuation_upside":
        return valuation_score(row, text)
    if name in {
        "trend_regime",
        "pullback_setup",
        "single_needle_washout",
        "macd_phase_confirmation",
        "impulse_confirmation",
        "technical_regime",
        "accumulation_quality",
    }:
        technical = row.get("technical") or {}
        return float(technical.get(name) or 0)
    raise ValueError(f"Unknown component: {name}")


def score_row(row: dict[str, Any], preset: dict[str, Any], thesis_dir: Path) -> dict[str, Any]:
    symbol = row.get("symbol") or ""
    text = thesis_text(symbol, thesis_dir)
    components = []
    positive_weight = 0.0
    weighted = 0.0
    penalty = 0.0

    for component in preset.get("components", []):
        name = component["name"]
        weight = float(component["weight"])
        raw = component_score(name, row, text, preset)
        components.append({"name": name, "weight": weight, "score": round(raw, 1)})
        if weight >= 0:
            positive_weight += weight
            weighted += raw * weight
        else:
            penalty += raw * abs(weight) / 100

    base_score = weighted / positive_weight if positive_weight else 0.0
    final_score = clamp(base_score - penalty)
    action = action_for_score(final_score, preset)
    return {
        "symbol": symbol,
        "score": round(final_score, 1),
        "action": action["label"],
        "next_step": action["next_step"],
        "cms": row.get("cms"),
        "quintile": row.get("quintile"),
        "stability": row.get("stability"),
        "vam": row.get("vam"),
        "vm_score": row.get("vm_score"),
        "pe_rank": row.get("pe_rank"),
        "components": components,
        "technical": row.get("technical"),
        "has_thesis": bool(text),
    }


def action_for_score(score: float, preset: dict[str, Any]) -> dict[str, str]:
    actions = sorted(preset.get("actions", []), key=lambda x: x["min_score"], reverse=True)
    for action in actions:
        if score >= float(action["min_score"]):
            return action
    return {"label": "Unrated", "next_step": "No action"}


def render_table(results: list[dict[str, Any]], preset: dict[str, Any]) -> None:
    print(f"\n{preset.get('label', preset.get('name'))} — {preset.get('horizon', '')}")
    print(f"扫描时间: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} Asia/Shanghai")
    print(f"候选数量: {len(results)}\n")
    header = f"{'Rank':<5} {'Symbol':<12} {'Score':>6} {'Action':<18} {'CMS':>7} {'Q':<3} {'VM':>7} {'Next Step'}"
    print(header)
    print("-" * len(header))
    for idx, item in enumerate(results, 1):
        vm = item.get("vm_score")
        vm_text = f"{float(vm):+.3f}" if vm is not None else "N/A"
        cms = item.get("cms")
        cms_text = f"{float(cms):+.3f}" if cms is not None else "N/A"
        print(
            f"{idx:<5} {item['symbol']:<12} {item['score']:>6.1f} "
            f"{item['action']:<18} {cms_text:>7} {str(item.get('quintile') or ''):<3} "
            f"{vm_text:>7} {item['next_step']}"
        )
    print("\n以上为研究筛选结果，不构成投资建议或交易指令。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preset stock screener for NeoAlpha")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", help="逗号分隔标的列表，如 AAPL.US,MSFT.US,NVDA.US")
    group.add_argument("--from-thesis", action="store_true", help="扫描 thesis-tracker 中所有标的")
    group.add_argument("--thesis-dir", help="扫描指定 thesis 目录")
    group.add_argument("--momentum-json", help="读取已生成的 screen_momentum JSON，便于复用或测试")
    parser.add_argument("--preset", default="short_term_momentum", help="preset 名称或 JSON 路径")
    parser.add_argument("--top", type=int, default=20, help="输出前 N 名")
    parser.add_argument("--min-score", type=float, default=None, help="最低综合分过滤")
    parser.add_argument("--daily-bars", type=int, default=DEFAULT_DAILY_BARS, help="日线技术因子读取 K 线数量")
    parser.add_argument("--technical-cache-hours", type=float, default=DEFAULT_TECH_CACHE_HOURS, help="日线 K 线缓存有效小时数，0 表示禁用缓存")
    parser.add_argument("--kline-delay", type=float, default=DEFAULT_KLINE_DELAY, help="逐标的拉取日线 K 线后的限速等待秒数")
    parser.add_argument("--no-technical", action="store_true", help="禁用日线技术因子，只使用原有动量/文本/估值评分")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    preset = load_preset(args.preset)
    thesis_dir = Path(args.thesis_dir).expanduser() if args.thesis_dir else THESIS_DIR

    if args.momentum_json:
        scan = json.loads(Path(args.momentum_json).read_text(encoding="utf-8"))
    else:
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        else:
            symbols = load_thesis_symbols(thesis_dir)
        if not symbols:
            raise SystemExit("No symbols to scan.")
        scan = run_momentum_scan(symbols)

    rows = scan.get("results", [])
    if not args.no_technical:
        technical = load_technical_map(
            [row.get("symbol") for row in rows if row.get("symbol")],
            bars=args.daily_bars,
            cache_hours=args.technical_cache_hours,
            delay=args.kline_delay,
        )
        for row in rows:
            symbol = row.get("symbol")
            row["technical"] = technical.get(symbol, {"available": False, "reason": "missing symbol"})

    scored = [score_row(row, preset, thesis_dir) for row in rows]
    if args.min_score is not None:
        scored = [row for row in scored if row["score"] >= args.min_score]
    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = scored[: args.top]

    if args.json:
        print(json.dumps({
            "scan_time": datetime.now(TZ).isoformat(),
            "preset": preset,
            "results": scored,
        }, ensure_ascii=False, indent=2))
    else:
        render_table(scored, preset)


if __name__ == "__main__":
    main()
