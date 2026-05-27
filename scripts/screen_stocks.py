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
DEFAULT_GROUPS_FILE = Path(
    os.environ.get("NEOALPHA_SYMBOL_GROUPS_FILE", str(DEFAULT_THESIS_DIR.parent / "symbol-groups.json"))
).expanduser()
MOMENTUM_SCANNER = SKILL / "scripts" / "screen_momentum.py"
TZ = timezone(timedelta(hours=8))
TECH_CACHE_DIR = Path(os.environ.get("NEOALPHA_TECH_CACHE_DIR", "~/.cache/neoalpha/kline")).expanduser()
DEFAULT_TECH_CACHE_HOURS = float(os.environ.get("NEOALPHA_TECH_CACHE_HOURS", "6"))
DEFAULT_KLINE_DELAY = float(os.environ.get("NEOALPHA_KLINE_DELAY", "0.2"))
BENCHMARK_SYMBOLS = {
    ".US": "SPY.US",
    ".HK": "2800.HK",
    ".SH": "000300.SH",
    ".SZ": "000300.SH",
}
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


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def parse_symbol_list(value: Any) -> list[str]:
    if isinstance(value, str):
        parts = re.split(r"[\s,]+", value)
    elif isinstance(value, list):
        parts = value
    else:
        return []
    return [normalize_symbol(str(part)) for part in parts if str(part).strip()]


def load_symbol_groups(path: Path = DEFAULT_GROUPS_FILE) -> dict[str, list[str]]:
    if not path.exists():
        raise SystemExit(f"Symbol group file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Symbol group file must be a JSON object.")
    groups: dict[str, list[str]] = {}
    for name, value in data.items():
        if isinstance(value, dict):
            value = value.get("symbols")
        symbols = parse_symbol_list(value)
        if symbols:
            groups[str(name)] = symbols
    return groups


def resolve_group_symbols(group_names: list[str] | None, group_file: str | None) -> list[str]:
    if not group_names:
        return []
    groups = load_symbol_groups(Path(group_file).expanduser() if group_file else DEFAULT_GROUPS_FILE)
    missing = [name for name in group_names if name not in groups]
    if missing:
        available = ", ".join(sorted(groups)) or "none"
        raise SystemExit(f"Symbol group not found: {', '.join(missing)}. Available groups: {available}")
    symbols: list[str] = []
    seen: set[str] = set()
    for name in group_names:
        for symbol in groups[name]:
            if symbol not in seen:
                symbols.append(symbol)
                seen.add(symbol)
    return symbols


def market_suffixes(market: str | None) -> tuple[str, ...]:
    if not market:
        return ()
    normalized = market.upper()
    if normalized in {"CN", "A"}:
        return (".SH", ".SZ")
    if normalized in {"SH", "SZ", "HK", "US"}:
        return (f".{normalized}",)
    raise SystemExit(f"Unsupported market: {market}")


def filter_symbols_by_market(symbols: list[str], market: str | None) -> list[str]:
    suffixes = market_suffixes(market)
    if not suffixes:
        return symbols
    return [symbol for symbol in symbols if symbol.upper().endswith(suffixes)]


def filter_symbols_by_group(symbols: list[str], group_symbols: list[str]) -> list[str]:
    if not group_symbols:
        return symbols
    allowed = set(group_symbols)
    return [symbol for symbol in symbols if normalize_symbol(symbol) in allowed]


def filter_scan_rows(rows: list[dict[str, Any]], market: str | None, group_symbols: list[str]) -> list[dict[str, Any]]:
    symbols = [normalize_symbol(str(row.get("symbol") or "")) for row in rows]
    symbols = filter_symbols_by_market(symbols, market)
    symbols = filter_symbols_by_group(symbols, group_symbols)
    allowed = set(symbols)
    return [row for row in rows if normalize_symbol(str(row.get("symbol") or "")) in allowed]


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


def _detect_market_suffix(symbol: str) -> str:
    for suffix in (".US", ".HK", ".SH", ".SZ"):
        if symbol.upper().endswith(suffix):
            return suffix
    return ".US"


def fetch_benchmark_klines(
    symbols: list[str],
    bars: int = DEFAULT_DAILY_BARS,
    cache_hours: float = DEFAULT_TECH_CACHE_HOURS,
    delay: float = DEFAULT_KLINE_DELAY,
) -> dict[str, list[float]]:
    """Fetch benchmark index klines for relative strength calculation.

    Returns a dict mapping market suffix to a list of benchmark close prices.
    Only fetches benchmarks for markets that appear in the symbol list.
    """
    needed_suffixes: set[str] = set()
    for symbol in symbols:
        needed_suffixes.add(_detect_market_suffix(symbol))
    benchmarks: dict[str, list[float]] = {}
    for suffix in needed_suffixes:
        bench_symbol = BENCHMARK_SYMBOLS.get(suffix)
        if not bench_symbol:
            continue
        if bench_symbol in benchmarks:
            continue
        rows = fetch_daily_klines(bench_symbol, bars=bars, cache_hours=cache_hours, delay=delay)
        if rows:
            benchmarks[suffix] = [_to_float(r["close"]) for r in rows]
    # Map .SZ to same as .SH if not separately fetched
    if ".SH" in benchmarks and ".SZ" not in benchmarks:
        benchmarks[".SZ"] = benchmarks[".SH"]
    return benchmarks


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


def technical_factors(rows: list[dict[str, Any]], benchmark_closes: list[float] | None = None) -> dict[str, Any]:
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
    yellow_dist = abs(close - yellow_now) / yellow_now * 100 if yellow_now and close else 100
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

    # --- NEW v2 TECHNICAL SCORES ---

    # VCP: Volatility Contraction Pattern detection
    lookback_vcp = min(120, len(c) - 5)
    swing_highs_vcp: list[tuple[int, float]] = []
    swing_lows_vcp: list[tuple[int, float]] = []
    for i in range(len(c) - lookback_vcp, len(c) - 2):
        if i < 3:
            continue
        if h[i] > h[i - 1] and h[i] > h[i - 2] and h[i] >= h[i + 1] and h[i] >= h[i + 2]:
            swing_highs_vcp.append((i, h[i]))
        if l[i] < l[i - 1] and l[i] < l[i - 2] and l[i] <= l[i + 1] and l[i] <= l[i + 2]:
            swing_lows_vcp.append((i, l[i]))
    drawdowns_vcp: list[float] = []
    vol_at_trough_vcp: list[float] = []
    for sh_pos, sh_price in swing_highs_vcp:
        next_low = None
        for sl_pos, sl_price in swing_lows_vcp:
            if sl_pos > sh_pos:
                next_low = (sl_pos, sl_price)
                break
        if next_low:
            dd_pct = (sh_price - next_low[1]) / sh_price * 100 if sh_price else 0
            avg_vol_vcp = sum(v[max(0, next_low[0] - 2) : next_low[0] + 1]) / min(3, next_low[0] + 1) if v else volume
            drawdowns_vcp.append(dd_pct)
            vol_at_trough_vcp.append(avg_vol_vcp)
    vcp_contracting = False
    vcp_vol_drying = False
    vcp_higher_lows = False
    vcp_near_pivot = False
    if len(drawdowns_vcp) >= 3:
        last3dd = drawdowns_vcp[-3:]
        vcp_contracting = all(last3dd[i] > last3dd[i + 1] * 0.65 for i in range(len(last3dd) - 1)) and last3dd[-1] < last3dd[0] * 0.7
        if len(vol_at_trough_vcp) >= 3:
            last3v = vol_at_trough_vcp[-3:]
            vcp_vol_drying = last3v[-1] < last3v[0] * 0.7
        if len(swing_lows_vcp) >= 3:
            last3l = [sl[1] for sl in swing_lows_vcp[-3:]]
            vcp_higher_lows = all(last3l[i] < last3l[i + 1] for i in range(len(last3l) - 1))
    if swing_highs_vcp:
        recent_pivot = max(sh[1] for sh in swing_highs_vcp[-3:])
        vcp_near_pivot = close >= recent_pivot * 0.95
    vcp_score = clamp(
        (35 if vcp_contracting else 0)
        + (20 if vcp_vol_drying else 0)
        + (15 if vcp_higher_lows else 0)
        + (20 if vcp_near_pivot else 0)
        + (10 if trend_ok else 0)
    )

    # Candlestick Reversal Patterns
    body_size = abs(close - open_)
    upper_shadow_cs = high - max(close, open_)
    lower_shadow_cs = min(close, open_) - low
    total_range_cs = high - low if high > low else 0.001
    is_hammer = (
        lower_shadow_cs >= body_size * 2
        and upper_shadow_cs <= body_size * 0.3
        and total_range_cs > 0
        and close > open_
        and len(c) > 3
        and c[-2] < c[-3]
    )
    prev_body = abs(c[-2] - o[-2]) if len(c) > 2 else 0
    is_bullish_engulfing = (
        len(c) > 4
        and close > open_
        and c[-2] < o[-2]
        and open_ <= c[-2]
        and close >= o[-2]
        and body_size > prev_body
        and c[-3] < c[-4]
    )
    is_morning_star = False
    if len(c) >= 4:
        day1_bearish = c[-3] < o[-3] and abs(c[-3] - o[-3]) / max(o[-3], 0.01) > 0.01
        day2_small = abs(c[-2] - o[-2]) / max(c[-2], 0.01) < 0.005
        day3_bullish = close > open_ and close > (c[-3] + o[-3]) / 2
        is_morning_star = day1_bearish and day2_small and day3_bullish
    is_doji_confirm = (
        len(c) > 2
        and abs(c[-2] - o[-2]) / max(c[-2], 0.01) < 0.003
        and close > open_
        and close > c[-2]
    )
    is_piercing = (
        len(c) > 2
        and c[-2] < o[-2]
        and open_ < c[-2]
        and close > open_
        and close > (c[-2] + o[-2]) / 2
        and close < o[-2]
    )
    at_support = white_dist <= 3 or yellow_dist <= 4 or bbi_dist <= 3
    vol_ma5 = sum(v[-5:]) / 5 if len(v) >= 5 else volume
    vol_confirm_cs = volume > vol_ma5 * 1.2
    pattern_scores_cs: list[float] = []
    if is_morning_star:
        pattern_scores_cs.append(45)
    if is_hammer and at_support:
        pattern_scores_cs.append(40)
    elif is_hammer:
        pattern_scores_cs.append(25)
    if is_bullish_engulfing:
        pattern_scores_cs.append(35)
    if is_doji_confirm:
        pattern_scores_cs.append(30)
    if is_piercing:
        pattern_scores_cs.append(25)
    best_pattern = max(pattern_scores_cs) if pattern_scores_cs else 0
    candlestick_score = clamp(
        best_pattern
        + (15 if vol_confirm_cs and best_pattern > 0 else 0)
        + (10 if at_support and best_pattern > 0 else 0)
        + (10 if trend_ok and best_pattern > 0 else 0)
    )

    # Chan Theory Divergence (simplified: MACD area comparison)
    macd_hist = data["macd"]
    zero_crosses: list[tuple[str, int]] = []
    for i in range(1, len(macd_hist)):
        if macd_hist[i - 1] <= 0 < macd_hist[i]:
            zero_crosses.append(("up", i))
        elif macd_hist[i - 1] >= 0 > macd_hist[i]:
            zero_crosses.append(("down", i))
    neg_areas: list[dict[str, Any]] = []
    current_neg_start: int | None = None
    for direction, pos in zero_crosses:
        if direction == "down":
            current_neg_start = pos
        elif direction == "up" and current_neg_start is not None:
            area = sum(abs(macd_hist[jj]) for jj in range(current_neg_start, min(pos, len(macd_hist))))
            price_low = min(l[current_neg_start : min(pos, len(l))])
            neg_areas.append({"start": current_neg_start, "end": pos, "area": area, "price_low": price_low})
            current_neg_start = None
    if current_neg_start is not None and current_neg_start < len(macd_hist) - 1:
        area = sum(abs(macd_hist[jj]) for jj in range(current_neg_start, len(macd_hist)))
        price_low = min(l[current_neg_start : len(l)])
        neg_areas.append({"start": current_neg_start, "end": len(macd_hist) - 1, "area": area, "price_low": price_low})
    bottom_divergence = False
    if len(neg_areas) >= 2:
        prev_neg = neg_areas[-2]
        curr_neg = neg_areas[-1]
        if curr_neg["price_low"] <= prev_neg["price_low"] * 1.02 and curr_neg["area"] < prev_neg["area"] * 0.85:
            bottom_divergence = True
    chan_second_buy = False
    up_crosses = [(d, p) for d, p in zero_crosses if d == "up"]
    if up_crosses and up_crosses[-1][1] > len(c) - 15:
        if data["dif"][-1] > data["dea"][-1] or data["dif"][-1] > data["dif"][-3]:
            chan_second_buy = True
    macd_area_shrinking = len(neg_areas) >= 2 and neg_areas[-1]["area"] < neg_areas[-2]["area"]
    chan_vol_shrink = False
    if neg_areas:
        na = neg_areas[-1]
        na_vols = v[na["start"] : min(na["end"] + 1, len(v))]
        if na_vols and len(v) > 40:
            chan_vol_shrink = sum(na_vols) / max(len(na_vols), 1) < sum(v[-40:-20]) / max(20, 1) * 0.6
    chan_score = clamp(
        (45 if bottom_divergence else 0)
        + (35 if chan_second_buy else 0)
        + (25 if macd_area_shrinking and not bottom_divergence else 0)
        + (15 if trend_ok else 0)
        + (10 if chan_vol_shrink else 0)
    )

    # Bollinger Squeeze (TTM Squeeze)
    ma20_list = _ma(c, 20)
    boll_squeeze_val = 0.0
    if ma20_list[-1] is not None and ma20_list[-1] > 0:
        bb_stds: list[float] = []
        for bi in range(max(20, len(c) - 120), len(c)):
            if ma20_list[bi] is not None:
                variance = sum((c[bj] - ma20_list[bj]) ** 2 for bj in range(max(0, bi - 19), bi + 1) if ma20_list[bj] is not None) / 20
                bb_stds.append(variance ** 0.5)
        current_std = bb_stds[-1] if bb_stds else 0
        bb_upper_val = ma20_list[-1] + 2 * current_std
        bb_lower_val = ma20_list[-1] - 2 * current_std
        bb_width = (bb_upper_val - bb_lower_val) / ma20_list[-1] * 100
        bb_widths = [(2 * s * 2) / ma20_list[-1] * 100 for s in bb_stds] if bb_stds else [bb_width]
        bb_width_rank = sum(1 for bw in bb_widths if bw <= bb_width) / max(len(bb_widths), 1) * 100
        tr_list: list[float] = []
        for ti in range(1, len(c)):
            tr_list.append(max(h[ti] - l[ti], abs(h[ti] - c[ti - 1]), abs(l[ti] - c[ti - 1])))
        atr14 = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else (sum(tr_list) / max(len(tr_list), 1))
        ema20_val = _ema(c, 20)[-1]
        kc_upper_val = ema20_val + 1.5 * atr14
        kc_lower_val = ema20_val - 1.5 * atr14
        squeeze_on = bb_upper_val < kc_upper_val and bb_lower_val > kc_lower_val
        price_above_mid = close > ma20_list[-1]
        mom_direction = close > c[-13] if len(c) > 13 else False
        boll_squeeze_val = clamp(
            (35 if bb_width_rank <= 20 else (15 if bb_width_rank <= 35 else 0))
            + (25 if squeeze_on else 0)
            + (15 if price_above_mid else 0)
            + (15 if mom_direction else 0)
            + (10 if trend_ok else 0)
        )

    # Volume-Price Divergence
    obv: list[float] = [0.0]
    for vi in range(1, len(c)):
        if c[vi] > c[vi - 1]:
            obv.append(obv[-1] + v[vi])
        elif c[vi] < c[vi - 1]:
            obv.append(obv[-1] - v[vi])
        else:
            obv.append(obv[-1])
    price_declining_20 = c[-1] < c[-21] if len(c) > 21 else False
    obv_not_declining = obv[-1] >= obv[-21] if len(obv) > 21 else False
    obv_divergence = price_declining_20 and obv_not_declining
    selling_exhaust = False
    if len(c) > 10:
        down_vols = [v[di] for di in range(len(c) - 10, len(c)) if c[di] < c[di - 1]]
        if len(down_vols) >= 3:
            selling_exhaust = down_vols[-1] < down_vols[0] * 0.7
    healthy_vol = False
    if len(c) > 20:
        up_vol = sum(v[ui] for ui in range(len(c) - 20, len(c)) if c[ui] > c[ui - 1])
        down_vol = sum(v[ui] for ui in range(len(c) - 20, len(c)) if c[ui] < c[ui - 1])
        healthy_vol = up_vol > down_vol * 1.3 if down_vol > 0 else up_vol > 0
    ad_line: list[float] = [0.0]
    for ai in range(1, len(c)):
        clv = ((c[ai] - l[ai]) - (h[ai] - c[ai])) / (h[ai] - l[ai]) if h[ai] != l[ai] else 0
        ad_line.append(ad_line[-1] + clv * v[ai])
    ad_rising = len(ad_line) > 20 and ad_line[-1] > ad_line[-21]
    vol_price_div_score = clamp(
        (35 if obv_divergence else 0)
        + (25 if selling_exhaust else 0)
        + (20 if healthy_vol else 0)
        + (10 if ad_rising else 0)
        + (10 if trend_ok else 0)
    )

    # Trend Template (Minervini 8 conditions)
    ma50_list = _ma(c, 50)
    ma150_list = _ma(c, 150)
    ma200_list = _ma(c, 200)
    ma50_now = _latest(ma50_list)
    ma150_now = _latest(ma150_list)
    ma200_now = _latest(ma200_list)
    ma200_1mo = _latest(ma200_list, 20)
    tt_conditions = 0
    if ma150_now and ma200_now:
        if close > ma150_now and close > ma200_now:
            tt_conditions += 1
        if ma150_now > ma200_now:
            tt_conditions += 1
    if ma200_now and ma200_1mo and ma200_now > ma200_1mo:
        tt_conditions += 1
    if ma50_now and ma150_now and ma200_now:
        if ma50_now > ma150_now and ma50_now > ma200_now:
            tt_conditions += 1
    if ma50_now and close > ma50_now:
        tt_conditions += 1
    lookback_52w = min(252, len(c))
    year_high = _hhv(h, lookback_52w)
    year_low = _llv(l, lookback_52w)
    if year_low > 0 and (close / year_low - 1) >= 0.30:
        tt_conditions += 1
    if year_high > 0 and (year_high / close - 1) <= 0.25:
        tt_conditions += 1
    if len(c) > 126 and c[-1] > c[-126]:
        tt_conditions += 1
    trend_template_val = clamp(tt_conditions / 8 * 100)

    # Wave Position / Stage Analysis
    wave_val = 50.0
    if ma200_now and ma200_1mo and ma200_now > 0:
        ma200_slope = (ma200_now - ma200_1mo) / ma200_1mo * 100
        if ma200_slope > 0.5 and close > ma200_now and ma150_now and ma150_now > ma200_now:
            wave_val = 85.0
            if ma50_now and ma50_now > ma150_now:
                wave_val = 95.0
        elif abs(ma200_slope) <= 0.5 and abs(close - ma200_now) / ma200_now < 0.05:
            wave_val = 30.0
        elif ma200_slope > 0 and close < ma200_now:
            wave_val = 45.0
        elif ma200_slope < -0.5:
            wave_val = 5.0 if close < ma200_now else 20.0
        else:
            wave_val = 40.0

    # Relative Strength vs Benchmark
    rs_val = 50.0
    if benchmark_closes and len(benchmark_closes) > 252 and len(c) > 252:
        def _period_rs(stock: list[float], bench: list[float], period: int) -> float:
            if len(stock) > period and len(bench) > period:
                stock_ret = stock[-1] / stock[-period - 1] - 1 if stock[-period - 1] else 0
                bench_ret = bench[-1] / bench[-period - 1] - 1 if bench[-period - 1] else 0
                return stock_ret - bench_ret
            return 0.0
        rs_63 = _period_rs(c, benchmark_closes, 63)
        rs_126 = _period_rs(c, benchmark_closes, 126)
        rs_189 = _period_rs(c, benchmark_closes, 189)
        rs_252 = _period_rs(c, benchmark_closes, 252)
        composite_rs = 0.4 * rs_63 + 0.2 * rs_126 + 0.2 * rs_189 + 0.2 * rs_252
        rs_val = clamp((composite_rs + 0.3) / 0.6 * 100)

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
        "vcp_pattern": round(vcp_score, 1),
        "candlestick_reversal": round(candlestick_score, 1),
        "chan_divergence": round(chan_score, 1),
        "bollinger_squeeze": round(boll_squeeze_val, 1),
        "volume_price_divergence": round(vol_price_div_score, 1),
        "trend_template": round(trend_template_val, 1),
        "wave_position": round(wave_val, 1),
        "relative_strength": round(rs_val, 1),
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
            "vcp_contracting": vcp_contracting,
            "vcp_near_pivot": vcp_near_pivot,
            "candlestick_pattern": best_pattern > 0,
            "bottom_divergence": bottom_divergence,
            "squeeze_on": squeeze_on if ma20_list[-1] is not None else False,
            "obv_divergence": obv_divergence,
            "trend_template_conditions": tt_conditions,
            "wave_stage": wave_val,
            "rs_score": round(rs_val, 1),
        },
    }


def load_technical_map(
    symbols: list[str],
    bars: int = DEFAULT_DAILY_BARS,
    cache_hours: float = DEFAULT_TECH_CACHE_HOURS,
    delay: float = DEFAULT_KLINE_DELAY,
    benchmarks: dict[str, list[float]] | None = None,
) -> dict[str, dict[str, Any]]:
    tech = {}
    for symbol in symbols:
        rows = fetch_daily_klines(symbol, bars=bars, cache_hours=cache_hours, delay=delay)
        bench = None
        if benchmarks:
            suffix = _detect_market_suffix(symbol)
            bench = benchmarks.get(suffix)
        tech[symbol] = technical_factors(rows, benchmark_closes=bench)
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
        "vcp_pattern",
        "candlestick_reversal",
        "chan_divergence",
        "bollinger_squeeze",
        "volume_price_divergence",
        "trend_template",
        "wave_position",
        "relative_strength",
    }:
        technical = row.get("technical") or {}
        return float(technical.get(name) or 0)
    raise ValueError(f"Unknown component: {name}")


def score_row(row: dict[str, Any], preset: dict[str, Any], thesis_dir: Path) -> dict[str, Any]:
    symbol = row.get("symbol") or ""
    text = thesis_text(symbol, thesis_dir)

    foundation_cfg = preset.get("foundation", {})
    foundation_components = foundation_cfg.get("components", preset.get("components", []))
    
    # Calculate foundation score
    positive_weight = 0.0
    weighted = 0.0
    penalty = 0.0
    comp_details: list[dict[str, Any]] = []

    for component in foundation_components:
        name = component["name"]
        weight = float(component["weight"])
        raw = component_score(name, row, text, preset)
        comp_details.append({"name": name, "weight": weight, "score": round(raw, 1)})
        if weight >= 0:
            positive_weight += weight
            weighted += raw * weight
        else:
            penalty += raw * abs(weight) / 100

    foundation_score = clamp((weighted / positive_weight if positive_weight else 0.0) - penalty)

    # Evaluate highlight signals
    highlights_cfg = preset.get("highlights", [])
    triggered_highlights: list[dict[str, Any]] = []
    all_highlight_details: list[dict[str, Any]] = []

    for hl in highlights_cfg:
        hl_name = hl["name"]
        threshold = float(hl.get("threshold", 50))
        hl_label = hl.get("label", hl_name)
        raw = component_score(hl_name, row, text, preset)
        detail = {"name": hl_name, "label": hl_label, "score": round(raw, 1), "threshold": threshold, "triggered": raw >= threshold}
        all_highlight_details.append(detail)
        if raw >= threshold:
            triggered_highlights.append({"name": hl_name, "label": hl_label, "confidence": round(raw, 1)})

    # Match action
    action = _match_v2_action(foundation_score, len(triggered_highlights), preset)

    # Composite score for sorting: foundation + highlight bonus
    composite = foundation_score + sum(h["confidence"] * 0.15 for h in triggered_highlights)

    return {
        "symbol": symbol,
        "score": round(composite, 1),
        "foundation_score": round(foundation_score, 1),
        "highlights_count": len(triggered_highlights),
        "highlights": triggered_highlights,
        "action": action["label"],
        "next_step": action["next_step"],
        "cms": row.get("cms"),
        "quintile": row.get("quintile"),
        "stability": row.get("stability"),
        "vam": row.get("vam"),
        "vm_score": row.get("vm_score"),
        "pe_rank": row.get("pe_rank"),
        "foundation_components": comp_details,
        "highlight_details": all_highlight_details,
        "technical": row.get("technical"),
        "has_thesis": bool(text),
    }


def _parse_condition(condition: str, foundation: float, highlights: int) -> bool:
    """Parse simple condition expressions like 'foundation>=55 && highlights>=2'."""
    if condition == "default":
        return True
    parts = [p.strip() for p in condition.split("&&")]
    for part in parts:
        for op in [">=", "<=", ">", "<", "=="]:
            if op in part:
                lhs, rhs = part.split(op, 1)
                lhs = lhs.strip()
                rhs_val = float(rhs.strip())
                if lhs == "foundation":
                    lhs_val = foundation
                elif lhs == "highlights":
                    lhs_val = float(highlights)
                else:
                    return False
                if op == ">=" and not (lhs_val >= rhs_val):
                    return False
                if op == "<=" and not (lhs_val <= rhs_val):
                    return False
                if op == ">" and not (lhs_val > rhs_val):
                    return False
                if op == "<" and not (lhs_val < rhs_val):
                    return False
                if op == "==" and not (lhs_val == rhs_val):
                    return False
                break
    return True


def _match_v2_action(foundation: float, highlights_count: int, preset: dict[str, Any]) -> dict[str, str]:
    """Match action based on v2 condition expressions."""
    for action in preset.get("actions", []):
        condition = action.get("condition", "default")
        if _parse_condition(condition, foundation, highlights_count):
            return action
    return {"label": "Unrated", "next_step": "No action", "condition": "default"}


def render_table(results: list[dict[str, Any]], preset: dict[str, Any]) -> None:
    print(f"\n{preset.get('label', preset.get('name'))} — {preset.get('horizon', '')}")
    print(f"架构: 基座+亮点 v2 | 基座合格线: {preset.get('foundation', {}).get('min_score', 'N/A')}")
    print(f"扫描时间: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} Asia/Shanghai")
    print(f"候选数量: {len(results)}\n")
    header = f"{'Rank':<5} {'Symbol':<12} {'Base':>5} {'HL':>3} {'Score':>6} {'Action':<18} {'Highlights':<40} {'Next Step'}"
    print(header)
    print("-" * max(len(header), 120))
    for idx, item in enumerate(results, 1):
        hl_names = ", ".join(h["label"] for h in item.get("highlights", []))
        if not hl_names:
            hl_names = "—"
        if len(hl_names) > 38:
            hl_names = hl_names[:35] + "..."
        print(
            f"{idx:<5} {item['symbol']:<12} {item.get('foundation_score', 0):>5.1f} "
            f"{item.get('highlights_count', 0):>3} {item['score']:>6.1f} "
            f"{item['action']:<18} {hl_names:<40} {item['next_step']}"
        )
    print("\n以上为研究筛选结果，不构成投资建议或交易指令。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preset stock screener for NeoAlpha")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", help="逗号分隔标的列表，如 AAPL.US,MSFT.US,NVDA.US")
    group.add_argument("--from-thesis", action="store_true", help="扫描 thesis-tracker 中所有标的")
    group.add_argument("--thesis-dir", help="扫描指定 thesis 目录")
    group.add_argument("--group", action="append", dest="groups", help="扫描命名标的分组；可重复使用，如 --group ai --group semiconductor")
    group.add_argument("--momentum-json", help="读取已生成的 screen_momentum JSON，便于复用或测试")
    parser.add_argument("--preset", default="short_term_momentum", help="preset 名称或 JSON 路径")
    parser.add_argument("--top", type=int, default=20, help="输出前 N 名")
    parser.add_argument("--min-score", type=float, default=None, help="最低综合分过滤")
    parser.add_argument("--daily-bars", type=int, default=DEFAULT_DAILY_BARS, help="日线技术因子读取 K 线数量")
    parser.add_argument("--technical-cache-hours", type=float, default=DEFAULT_TECH_CACHE_HOURS, help="日线 K 线缓存有效小时数，0 表示禁用缓存")
    parser.add_argument("--kline-delay", type=float, default=DEFAULT_KLINE_DELAY, help="逐标的拉取日线 K 线后的限速等待秒数")
    parser.add_argument("--no-technical", action="store_true", help="禁用日线技术因子，只使用原有动量/文本/估值评分")
    parser.add_argument("--market", choices=["US", "HK", "CN", "A", "SH", "SZ"], help="按市场过滤标的；CN/A 表示 .SH 和 .SZ")
    parser.add_argument("--group-filter", action="append", help="在当前 universe 上按命名分组取交集；可重复使用")
    parser.add_argument("--group-file", help=f"命名标的分组 JSON 文件，默认 {DEFAULT_GROUPS_FILE}")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    preset = load_preset(args.preset)
    thesis_dir = Path(args.thesis_dir).expanduser() if args.thesis_dir else THESIS_DIR
    group_names = list((args.groups or []) + (args.group_filter or []))
    group_symbols = resolve_group_symbols(group_names, args.group_file)

    if args.momentum_json:
        scan = json.loads(Path(args.momentum_json).read_text(encoding="utf-8"))
        scan["results"] = filter_scan_rows(scan.get("results", []), args.market, group_symbols)
    else:
        if args.symbols:
            symbols = parse_symbol_list(args.symbols)
        elif args.groups:
            symbols = group_symbols
        else:
            symbols = load_thesis_symbols(thesis_dir)
        symbols = filter_symbols_by_market(symbols, args.market)
        if args.group_filter:
            symbols = filter_symbols_by_group(symbols, group_symbols)
        if not symbols:
            raise SystemExit("No symbols to scan.")
        scan = run_momentum_scan(symbols)

    rows = scan.get("results", [])
    if not args.no_technical:
        all_symbols = [row.get("symbol") for row in rows if row.get("symbol")]
        
        # Smart Cache Bypass Rule (v3.3.1): less than 10 symbols automatically forces fresh real-time data
        cache_hours = args.technical_cache_hours
        if len(all_symbols) < 10:
            print(f"[INFO] 扫描标的数量 ({len(all_symbols)}) < 10，自动关闭日线缓存以拉取最新盘中实时数据 (technical_cache_hours forced to 0.0)")
            cache_hours = 0.0

        benchmarks = fetch_benchmark_klines(
            all_symbols,
            bars=args.daily_bars,
            cache_hours=cache_hours,
            delay=args.kline_delay,
        )
        technical = load_technical_map(
            all_symbols,
            bars=args.daily_bars,
            cache_hours=cache_hours,
            delay=args.kline_delay,
            benchmarks=benchmarks,
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
            "market": args.market,
            "groups": group_names or [],
            "scanned_count": len(rows),
            "architecture": "v2_foundation_highlights",
            "results": scored,
        }, ensure_ascii=False, indent=2))
    else:
        render_table(scored, preset)


if __name__ == "__main__":
    main()
