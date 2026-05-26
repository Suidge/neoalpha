#!/usr/bin/env python3
"""Market strategy engine for NeoAlpha cron workflows.

Subcommands:
  premarket --market US|HK  Generate a structured daily strategy markdown file.
  live --market US|HK       Evaluate structured triggers and print NO_REPLY or alerts.
  close --market US|HK      Produce a compact close review from the strategy.

No trading/orders. Read-only market data via Longbridge CLI.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Dict, Iterable, List, Optional, Tuple

from market_health_scan import scan_market_health

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "neoalpha"
DEFAULT_THESIS_DIR = Path.home() / "Documents" / "neoalpha" / "thesis-tracker"
THESIS_DIR = Path(os.environ.get("INVESTMENT_THESIS_DIR", str(DEFAULT_THESIS_DIR))).expanduser()
STOCK_SCREENER = SKILL / "scripts" / "screen_stocks.py"
STRATEGY_DIR = ROOT / "memory" / "strategies"
ASSETS_FILE = SKILL / "tracking" / "us-market-assets.md"
PREMARKET_PROMPT_PATHS = {
    "US": STRATEGY_DIR / "us-premarket-prompt.md",
    "HK": STRATEGY_DIR / "hk-premarket-prompt.md",
}
POSITIONS_TRACKER = STRATEGY_DIR / "positions-tracker.md"
POSITIONS_CURRENT = STRATEGY_DIR / "portfolio" / "positions-current.json"
TZ = dt.timezone(dt.timedelta(hours=8))
TODAY = dt.datetime.now(TZ).date().isoformat()
MARKET_TZ = {"US": ZoneInfo("America/New_York"), "HK": ZoneInfo("Asia/Hong_Kong"), "CN": ZoneInfo("Asia/Shanghai")}
MARKET_SESSIONS = {
    "US": (dt.time(9, 30), dt.time(16, 0)),
    "HK": (dt.time(9, 30), dt.time(16, 0)),
    "CN": (dt.time(9, 30), dt.time(15, 0)),
}
MAX_OWNER_PROMPT_CHARS = 800
MAX_POSITIONS_TRACKER_CHARS = 1400
MAX_NEWS_TITLES = 5


def market_today(market: str) -> str:
    return dt.datetime.now(MARKET_TZ.get(market, TZ)).date().isoformat()

MARKET_CONFIG = {
    "US": {
        "suffix": ".US",
        "strategy_suffixes": [".US"],
        "strategy": STRATEGY_DIR / "us-daily.md",
        "quote_core": [".SPX.US", ".IXIC.US", ".DJI.US", ".VIX.US", "SPY.US", "QQQ.US", "TLT.US", "UUP.US", "EEM.US", "FXI.US", "IBIT.US"],
        "index_symbols": [".SPX.US", ".IXIC.US", ".DJI.US", ".VIX.US"],
        "default_symbols": ["INTC.US", "NVDA.US", "AAPL.US", "GOOG.US", "META.US", "TSLA.US", "AMD.US", "QCOM.US", "GLD.US", "SLV.US", "USO.US", "TLT.US", "UUP.US", "EEM.US", "FXI.US", "IBIT.US"],
        "market_code": "US",
        "title": "US Market Strategy",
        "cn": "美股",
    },
    "HK": {
        "suffix": ".HK",
        "strategy_suffixes": [".HK", ".SZ", ".SH"],
        "strategy": STRATEGY_DIR / "hk-daily.md",
        "quote_core": ["HSTECH.HK", "000001.SH", "399001.SZ", "399006.SZ", "000300.SH", "700.HK", "9988.HK", "3690.HK", "1810.HK", "2228.HK", "7226.HK"],
        "index_symbols": ["HSTECH.HK", "000001.SH", "399001.SZ", "399006.SZ", "000300.SH"],
        "default_symbols": ["700.HK", "9988.HK", "3690.HK", "1810.HK", "2228.HK", "7226.HK"],
        "market_code": "HK",
        "title": "HK Market Strategy",
        "cn": "港股",
    },
}

HK_OVERNIGHT_US_MAP = [
    {"us_symbol": "KWEB.US", "hk_symbol": "HSTECH.HK", "name": "金龙/中概互联网 ETF", "role": "港股科技情绪锚"},
    {"us_symbol": "TCEHY.US", "hk_symbol": "700.HK", "name": "腾讯 ADR", "role": "恒科最大权重之一"},
    {"us_symbol": "BABA.US", "hk_symbol": "9988.HK", "name": "阿里 ADR", "role": "恒科/中概风险偏好核心"},
    {"us_symbol": "MPNGY.US", "hk_symbol": "3690.HK", "name": "美团 ADR", "role": "本地生活/平台经济情绪"},
    {"us_symbol": "XIACY.US", "hk_symbol": "1810.HK", "name": "小米 ADR", "role": "硬件/汽车链情绪"},
]

SYMBOL_NAME_FALLBACKS = {
    ".SPX.US": "标普500指数",
    ".IXIC.US": "纳斯达克综合指数",
    ".DJI.US": "道琼斯工业指数",
    ".VIX.US": "VIX波动率指数",
    "SPY.US": "SPDR标普500 ETF",
    "QQQ.US": "纳斯达克100 ETF",
    "TLT.US": "20年期以上美国国债ETF",
    "UUP.US": "美元指数ETF",
    "EEM.US": "新兴市场ETF",
    "FXI.US": "中国大型股ETF",
    "IBIT.US": "iShares比特币信托",
    "INTC.US": "英特尔",
    "NVDA.US": "英伟达",
    "AAPL.US": "苹果",
    "GOOG.US": "Alphabet",
    "META.US": "Meta Platforms",
    "TSLA.US": "特斯拉",
    "AMD.US": "AMD",
    "QCOM.US": "高通",
    "GLD.US": "黄金ETF",
    "SLV.US": "白银ETF",
    "USO.US": "美国原油基金",
    "HSTECH.HK": "恒生科技指数",
    "000001.SH": "上证指数",
    "399001.SZ": "深证成指",
    "399006.SZ": "创业板指",
    "000300.SH": "沪深300",
    "700.HK": "腾讯控股",
    "9988.HK": "阿里巴巴-W",
    "3690.HK": "美团-W",
    "1810.HK": "小米集团-W",
    "2228.HK": "晶泰控股-P",
    "7226.HK": "XL二南方恒科",
}


def canonical_symbol(symbol: str) -> str:
    """Normalize strategy symbols to Longbridge quote symbols."""
    if symbol.startswith("."):
        return symbol
    dotted = "." + symbol
    if dotted in SYMBOL_NAME_FALLBACKS:
        return dotted
    return symbol


def symbol_market_code(symbol: str) -> Optional[str]:
    symbol = canonical_symbol(symbol)
    if symbol.endswith(".HK"):
        return "HK"
    if symbol.endswith(".SH") or symbol.endswith(".SZ"):
        return "CN"
    if symbol.endswith(".US"):
        return "US"
    return None


def run(cmd: List[str], timeout: int = 35) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "").strip() if isinstance(e.stdout, str) else "", "timeout"


def longbridge_json(args: List[str], timeout: int = 35) -> Any:
    code, out, err = run(["longbridge", *args, "--format", "json"], timeout=timeout)
    if code != 0 or not out:
        raise RuntimeError(f"longbridge {' '.join(args)} failed: {err or out or code}")
    return json.loads(out)


def safe_longbridge_json(args: List[str], timeout: int = 35) -> Any:
    try:
        return longbridge_json(args, timeout)
    except Exception:
        return None


def quote(symbols: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    unique = []
    aliases: Dict[str, str] = {}
    seen = set()
    for s in symbols:
        if not s:
            continue
        canonical = canonical_symbol(s)
        aliases[s] = canonical
        if canonical in seen:
            continue
        seen.add(canonical)
        unique.append(canonical)
    if not unique:
        return {}
    data = longbridge_json(["quote", *unique], timeout=45)
    if isinstance(data, dict):
        rows = data.get("data") or data.get("quotes") or [data]
    else:
        rows = data
    out = {}
    for row in rows or []:
        if isinstance(row, dict) and row.get("symbol"):
            out[row["symbol"]] = row
    for original, canonical in aliases.items():
        if original != canonical and canonical in out:
            out[original] = out[canonical]
    return out


def qnum(row: Dict[str, Any], key: str) -> Optional[float]:
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def rnum(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def pct(row: Dict[str, Any]) -> Optional[float]:
    if row.get("change_percentage") is not None:
        return qnum(row, "change_percentage")
    last = qnum(row, "last") or qnum(row, "last_done")
    prev = qnum(row, "prev_close")
    if last is None or not prev:
        return None
    return (last / prev - 1) * 100


def fmt_price(row: Optional[Dict[str, Any]]) -> str:
    if not row:
        return "N/A"
    last = row.get("last") or row.get("last_done") or row.get("price") or "N/A"
    p = pct(row)
    return f"{last} ({p:+.2f}%)" if p is not None else str(last)


def compact_text(text: str, limit: int) -> str:
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n...[truncated to {limit} chars]"


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def thesis_symbol_from_path(path: Path) -> str:
    if path.suffix != ".md":
        return ""
    match = re.match(r"^([A-Za-z0-9]+)\.(US|HK|SH|SZ)(?:-.+)?$", path.stem)
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}".upper()


def thesis_path(symbol: str) -> Optional[Path]:
    exact = THESIS_DIR / f"{symbol}.md"
    if exact.exists():
        return exact
    code, market = symbol.rsplit(".", 1)
    matches = sorted(THESIS_DIR.glob(f"{code}.{market}-*.md"))
    return matches[0] if matches else None


def prune_empty(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: v for k, v in ((k, prune_empty(v)) for k, v in value.items()) if v not in (None, [], {}, "")}
    if isinstance(value, list):
        return [v for v in (prune_empty(v) for v in value) if v not in (None, [], {}, "")]
    return value


def quote_display_name(row: Optional[Dict[str, Any]]) -> str:
    if not row:
        return ""
    for key in ("name", "stock_name", "security_name", "symbol_name", "short_name", "display_name", "description", "cn_name"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def thesis_name(symbol: str) -> str:
    p = thesis_path(symbol)
    if not p:
        return ""
    first = p.read_text(errors="replace").splitlines()[:1]
    if not first or not first[0].startswith("# "):
        return ""
    title = first[0].lstrip("# ").strip()
    title = re.sub(r"^Thesis:\s*", "", title, flags=re.I).strip()
    if title.startswith(symbol):
        title = title[len(symbol):].strip(" -—:：")
    title = re.sub(rf"[（(]\s*{re.escape(symbol)}\s*[）)]", "", title).strip()
    return title.strip()


def symbol_name(symbol: str, row: Optional[Dict[str, Any]] = None, monitor: Optional[Dict[str, Any]] = None) -> str:
    for source in (monitor or {}, row or {}):
        for key in ("name", "stock_name", "security_name", "symbol_name", "short_name", "display_name", "cn_name"):
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, str) and value.strip() and value.strip() != symbol:
                return value.strip()
    return quote_display_name(row) or thesis_name(symbol) or SYMBOL_NAME_FALLBACKS.get(symbol, "")


def display_symbol(symbol: str, row: Optional[Dict[str, Any]] = None, monitor: Optional[Dict[str, Any]] = None) -> str:
    name = symbol_name(symbol, row, monitor)
    return f"{symbol} {name}" if name else symbol


def trigger_level(trigger: Dict[str, Any]) -> Optional[float]:
    value = trigger.get("level", trigger.get("value"))
    if value is None:
        return None
    return float(value)


def trigger_reason(trigger: Dict[str, Any], fallback: str) -> str:
    return str(trigger.get("reason") or trigger.get("action") or fallback)


def brief_quote_line(label: str, row: Dict[str, Any]) -> str:
    last = qnum(row, "last") or qnum(row, "last_done")
    chg = pct(row)
    price = "N/A" if last is None else f"{last:g}"
    move = "N/A" if chg is None else f"{chg:+.2f}%"
    return f"{label} {price} {move}"


def quote_session(row: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    value = row.get(key)
    return value if isinstance(value, dict) else None


def quote_snapshot(row: Optional[Dict[str, Any]], market: str) -> Dict[str, Any]:
    """Return explicit quote buckets so models do not mix prior-close and premarket data."""
    row = row or {}
    regular = {
        "last": qnum(row, "last") or qnum(row, "last_done"),
        "prev_close": qnum(row, "prev_close"),
        "change_pct": pct(row) if row else None,
        "basis": "regular_session_vs_previous_close",
    }
    pre = quote_session(row, "pre_market_quote")
    post = quote_session(row, "post_market_quote")
    overnight = quote_session(row, "overnight_quote")

    def extended(src: Optional[Dict[str, Any]], basis: str) -> Optional[Dict[str, Any]]:
        if not src:
            return None
        last = qnum(src, "last") or qnum(src, "last_done")
        prev = qnum(src, "prev_close")
        change = (last / prev - 1) * 100 if last is not None and prev else pct(src)
        return {
            "last": rnum(last),
            "prev_close": rnum(prev),
            "change_pct": rnum(change),
            "timestamp": src.get("timestamp"),
            "basis": basis,
        }

    pre_data = extended(pre, "pre_market" if market == "US" else "auction_or_preopen")
    return prune_empty({
        "regular_session": {
            "last": rnum(regular["last"]),
            "prev_close": rnum(regular["prev_close"]),
            "change_pct": rnum(regular["change_pct"]),
            "basis": regular["basis"],
        },
        "pre_market": pre_data,
        "post_market": extended(post, "post_market"),
        "overnight": extended(overnight, "overnight"),
        "status": row.get("status"),
    })


def quote_interpretation_rules(market: str) -> List[str]:
    if market == "HK":
        return [
            "Use pre_market only when non-null; otherwise say no HK pre-open quote.",
            "regular_session.change_pct is prior regular-session move, not HK pre-open move.",
            "hk_overnight_us_context is ADR/China internet sentiment, not HK pre-open quote.",
        ]
    return [
        "Use pre_market only when non-null; otherwise say no US premarket quote.",
        "regular_session.change_pct is prior regular-session move, not US premarket move.",
        "Do not invent macro numbers; use news_titles/macro_events only as cited clues.",
    ]


def macro_events(market: str) -> List[Dict[str, Any]]:
    if market != "US":
        return []
    queries = [
        ("US economic data release today CPI PPI jobs", "macro_data", "high"),
        ("US stock futures Treasury yields dollar oil premarket today", "cross_asset", "medium"),
    ]
    events = []
    for query, tag, importance in queries:
        titles = news_search(query, 2)
        events.append({"tag": tag, "importance": importance, "query": query, "news_titles": titles})
    return events


def market_suffixes(market: str) -> List[str]:
    return list(MARKET_CONFIG[market].get("strategy_suffixes") or [MARKET_CONFIG[market]["suffix"]])


def thesis_symbols(market: str) -> List[str]:
    symbols = []
    suffixes = tuple(market_suffixes(market))
    for path in THESIS_DIR.glob("*.md"):
        symbol = thesis_symbol_from_path(path)
        if symbol.endswith(suffixes):
            symbols.append(symbol)
    return sorted(set(symbols))


def run_stock_screen(symbols: List[str], preset: str, top: int = 10) -> Dict[str, Any]:
    """Run preset stock screener on thesis symbols."""
    if not symbols or not STOCK_SCREENER.exists():
        return {"error": "stock screener unavailable", "results": []}
    syms_arg = ",".join(symbols[:30])
    try:
        code, out, err = run(
            [
                "python3",
                str(STOCK_SCREENER),
                "--symbols",
                syms_arg,
                "--preset",
                preset,
                "--top",
                str(top),
                "--json",
            ],
            timeout=60,
        )
        if code != 0 or not out:
            return {"error": err or f"exit {code}", "results": []}
        data = json.loads(out)
        preset_meta = data.get("preset") or {}
        results = []
        for r in (data.get("results") or [])[:top]:
            results.append({
                "symbol": r.get("symbol"),
                "score": r.get("score"),
                "action": r.get("action"),
                "next_step": r.get("next_step"),
                "cms": r.get("cms"),
                "quintile": r.get("quintile"),
                "vm_score": r.get("vm_score"),
                "components": r.get("components", [])[:4],
            })
        return {
            "preset": preset_meta.get("name") or preset,
            "label": preset_meta.get("label") or preset,
            "horizon": preset_meta.get("horizon"),
            "description": preset_meta.get("description"),
            "scanned_symbols": symbols[:30],
            "results": results,
        }
    except Exception as e:
        return {"error": str(e), "results": []}


def thesis_summary(symbol: str, max_chars: int = 120) -> str:
    p = thesis_path(symbol)
    if not p:
        return ""
    txt = p.read_text(errors="replace")
    m = re.search(r"## 论点陈述\n(.+?)(?:\n## |\Z)", txt, re.S)
    if not m:
        return ""
    s = re.sub(r"\s+", " ", m.group(1)).strip(" -\n")
    return s[:max_chars] + ("…" if len(s) > max_chars else "")


def extract_symbols_from_strategy(text: str, market: str) -> List[str]:
    suffix = "|".join(re.escape(sfx) for sfx in market_suffixes(market))
    return sorted(set(re.findall(rf"\b[A-Z0-9.]+(?:{suffix})\b", text)))


def load_strategy(path: Path, market: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    if not path.exists():
        return "", None
    text = path.read_text(errors="replace")
    m = re.search(r"```(?:proactive-trader|investment-system)-strategy\n(.*?)\n```", text, re.S)
    if not m:
        return text, None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return text, None
    if isinstance(data, dict):
        if isinstance(data.get("investment-system-strategy"), dict):
            data = data["investment-system-strategy"]
        elif isinstance(data.get("proactive-trader-strategy"), dict):
            data = data["proactive-trader-strategy"]
    if data.get("date") != market_today(market) or data.get("market") != market:
        return text, None
    return text, data


def market_code_today(code: str) -> str:
    return dt.datetime.now(MARKET_TZ.get(code, TZ)).date().isoformat()


def market_code_is_trading_day(code: str, date: Optional[str] = None) -> bool:
    date = date or market_code_today(code)
    data = safe_longbridge_json(["trading", "days", code, "--start", date, "--end", date], timeout=20)
    days = (data or {}).get("trading_days") if isinstance(data, dict) else None
    return date in (days or [])


def market_statuses() -> Dict[str, str]:
    data = safe_longbridge_json(["market-status"], timeout=20)
    statuses: Dict[str, str] = {}
    if isinstance(data, list):
        for r in data:
            if isinstance(r, dict) and r.get("market"):
                statuses[str(r["market"])] = str(r.get("status", "Unknown"))
    return statuses


def market_code_status(code: str) -> str:
    return market_statuses().get(code, "Unknown")


def market_is_trading_day(market: str, date: Optional[str] = None) -> bool:
    return market_code_is_trading_day(MARKET_CONFIG[market]["market_code"], date)


def market_status(market: str) -> str:
    return market_code_status(MARKET_CONFIG[market]["market_code"])


def regular_session_window(market: str) -> Tuple[dt.time, dt.time]:
    return MARKET_SESSIONS[MARKET_CONFIG[market]["market_code"]]


def market_code_regular_session_is_active(code: str, now: Optional[dt.datetime] = None) -> bool:
    """Return whether a market code is in a live regular session now."""
    if market_code_status(code) == "Trading":
        return True
    local_now = now.astimezone(MARKET_TZ[code]) if now else dt.datetime.now(MARKET_TZ[code])
    start, end = MARKET_SESSIONS[code]
    if not (start <= local_now.time() < end):
        return False
    return market_code_is_trading_day(code, local_now.date().isoformat())


def regular_session_is_active(market: str, now: Optional[dt.datetime] = None) -> bool:
    """Guard live alerts from using stale prior-session quote changes before open."""
    return market_code_regular_session_is_active(MARKET_CONFIG[market]["market_code"], now)


def trigger_set(symbol: str, row: Optional[Dict[str, Any]], market: str) -> List[Dict[str, Any]]:
    """Generate deterministic default triggers from current price."""
    last = qnum(row or {}, "last") or qnum(row or {}, "last_done")
    triggers = [
        {"type": "pct_change_abs_gte", "level": 5.0 if market == "HK" else 4.0, "severity": "medium", "reason": "日内波动显著"},
        {"type": "pct_change_abs_gte", "level": 8.0 if market == "HK" else 6.0, "severity": "high", "reason": "日内大幅异动"},
    ]
    if last:
        triggers.extend([
            {"type": "price_below", "level": round(last * 0.95, 3), "severity": "medium", "reason": "跌破盘前参考位 -5%"},
            {"type": "price_above", "level": round(last * 1.05, 3), "severity": "medium", "reason": "突破盘前参考位 +5%"},
        ])
    return triggers


def evaluate(row: Dict[str, Any], triggers: List[Dict[str, Any]]) -> List[str]:
    hits = []
    last = qnum(row, "last") or qnum(row, "last_done")
    chg = pct(row)
    for tr in triggers:
        typ = tr.get("type")
        level = trigger_level(tr)
        if level is None:
            continue
        reason = trigger_reason(tr, str(typ))
        if typ == "pct_change_abs_gte" and chg is not None and abs(chg) >= float(level):
            hits.append(f"{reason}: 涨跌幅 {chg:+.2f}% ≥ ±{level}%")
        elif typ == "pct_change_above" and chg is not None and chg >= float(level):
            hits.append(f"{reason}: 涨跌幅 {chg:+.2f}% ≥ {level}%")
        elif typ == "pct_change_below" and chg is not None and chg <= float(level):
            hits.append(f"{reason}: 涨跌幅 {chg:+.2f}% ≤ {level}%")
        elif typ == "price_above" and last is not None and last >= float(level):
            hits.append(f"{reason}: 现价 {last} ≥ {level}")
        elif typ == "price_below" and last is not None and last <= float(level):
            hits.append(f"{reason}: 现价 {last} ≤ {level}")
    return hits

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def now_iso() -> str:
    return dt.datetime.now(TZ).isoformat(timespec="seconds")


def live_state_path(market: str, date: Optional[str] = None) -> Path:
    date = date or market_today(market)
    return STRATEGY_DIR / f"{market.lower()}-live-state-{date}.json"


def load_live_state(market: str) -> Dict[str, Any]:
    path = live_state_path(market)
    if not path.exists():
        return {"schema_version": 1, "date": market_today(market), "market": market, "alerts": {}, "runs": []}
    try:
        data = json.loads(path.read_text(errors="replace"))
    except Exception:
        return {"schema_version": 1, "date": market_today(market), "market": market, "alerts": {}, "runs": []}
    if data.get("date") != market_today(market) or data.get("market") != market:
        return {"schema_version": 1, "date": market_today(market), "market": market, "alerts": {}, "runs": []}
    data.setdefault("alerts", {})
    data.setdefault("runs", [])
    return data


def save_live_state(market: str, state: Dict[str, Any]) -> None:
    STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
    path = live_state_path(market)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def trigger_severity(trigger: Dict[str, Any]) -> str:
    return str(trigger.get("severity") or "medium")


def evaluate_details(row: Dict[str, Any], triggers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    details = []
    last = qnum(row, "last") or qnum(row, "last_done")
    chg = pct(row)
    for idx, tr in enumerate(triggers):
        typ = tr.get("type")
        level = trigger_level(tr)
        if level is None:
            continue
        reason = trigger_reason(tr, str(typ or f"trigger_{idx}"))
        message = None
        distance = None
        if typ == "pct_change_abs_gte" and chg is not None and abs(chg) >= level:
            message = f"{reason}: 涨跌幅 {chg:+.2f}% ≥ ±{level:g}%"
            distance = abs(chg)
        elif typ == "pct_change_above" and chg is not None and chg >= level:
            message = f"{reason}: 涨跌幅 {chg:+.2f}% ≥ {level:g}%"
            distance = chg
        elif typ == "pct_change_below" and chg is not None and chg <= level:
            message = f"{reason}: 涨跌幅 {chg:+.2f}% ≤ {level:g}%"
            distance = abs(chg)
        elif typ == "price_above" and last is not None and last >= level:
            message = f"{reason}: 现价 {last} ≥ {level:g}"
            distance = abs(last / level - 1) * 100 if level else 0
        elif typ == "price_below" and last is not None and last <= level:
            message = f"{reason}: 现价 {last} ≤ {level:g}"
            distance = abs(last / level - 1) * 100 if level else 0
        if message:
            details.append({
                "key": f"{typ}:{reason}:{level:g}",
                "reason": reason,
                "message": message,
                "severity": trigger_severity(tr),
                "distance": distance or 0.0,
            })
    return details


def is_incremental_hit(symbol_state: Dict[str, Any], hit: Dict[str, Any], chg: Optional[float], price: Optional[float]) -> Tuple[bool, str]:
    prev = symbol_state.get("hits", {}).get(hit["key"])
    if not prev:
        return True, "首次触发"
    prev_alert_price = qnum(prev, "last_alert_price") or qnum(prev, "last_price")
    if price is not None and prev_alert_price:
        price_move = (price / prev_alert_price - 1) * 100
        if abs(price_move) >= 1.0:
            return True, f"较上次播报价变化 {price_move:+.2f}%"
    prev_rank = SEVERITY_RANK.get(str(prev.get("severity", "medium")), 2)
    rank = SEVERITY_RANK.get(str(hit.get("severity", "medium")), 2)
    if rank > prev_rank:
        return True, f"级别升级 {prev.get('severity')}→{hit.get('severity')}"
    prev_distance = float(prev.get("max_distance") or 0)
    distance = float(hit.get("distance") or 0)
    if distance >= max(prev_distance + 1.0, prev_distance * 1.2):
        return True, "偏离幅度继续扩大"
    if chg is not None:
        prev_abs = abs(float(symbol_state.get("max_abs_change") or 0))
        if abs(chg) >= max(prev_abs + 1.5, prev_abs * 1.25):
            return True, "日内波动显著扩大"
    return False, "重复触发"


def next_watch(row: Dict[str, Any], triggers: List[Dict[str, Any]]) -> str:
    last = qnum(row, "last") or qnum(row, "last_done")
    chg = pct(row)
    candidates = []
    for tr in triggers:
        typ = tr.get("type")
        level = trigger_level(tr)
        if level is None:
            continue
        reason = trigger_reason(tr, str(typ))
        if typ.startswith("pct_change") and chg is not None and abs(abs(chg) - abs(level)) > 0.01:
            candidates.append((abs(abs(chg) - abs(level)), f"{reason} {level:g}%"))
        elif typ.startswith("price") and last is not None and level:
            candidates.append((abs(last / level - 1), f"{reason} {level:g}"))
    if not candidates:
        return "观察触发后走势是否延续"
    return min(candidates, key=lambda x: x[0])[1]


def compact_focus(text: str, limit: int = 42) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def news_search(query: str, count: int = 3) -> List[str]:
    data = safe_longbridge_json(["news", "search", query, "--count", str(count)], timeout=30)
    if not isinstance(data, list):
        return []
    return [r.get("title", "")[:140] for r in data[:count] if isinstance(r, dict) and r.get("title")]





def hk_overnight_us_context() -> Optional[Dict[str, Any]]:
    """Collect prior US-session China ADR clues for HK premarket."""
    rows = quote([item["us_symbol"] for item in HK_OVERNIGHT_US_MAP])
    items = []
    for item in HK_OVERNIGHT_US_MAP:
        row = rows.get(item["us_symbol"])
        regular = quote_snapshot(row, "US").get("regular_session") if row else None
        items.append({
            **item,
            "quote": regular,
            "last": qnum(row or {}, "last") or qnum(row or {}, "last_done"),
            "change_pct": pct(row or {}) if row else None,
            "basis": "previous_us_regular_session_vs_prior_close",
            "interpretation": "用于判断港股开盘情绪，不等同于港股开盘前报价；需结合港股竞价/本地新闻确认。",
        })
    valid = [x for x in items if x.get("change_pct") is not None]
    avg = sum(x["change_pct"] for x in valid) / len(valid) if valid else None
    leaders = sorted(valid, key=lambda x: abs(x["change_pct"]), reverse=True)[:3]
    return {
        "basis": "US-listed China ADR / China internet ETF overnight performance",
        "importance": "high",
        "why_it_matters": "港股盘前需区别于美股盘前：恒科权重股和中概 ADR 隔夜表现通常决定开盘情绪与资金方向。",
        "items": items,
        "basket_avg_change_pct": avg,
        "top_movers": leaders,
    }

def load_premarket_prompt(market: str) -> Dict[str, Any]:
    """Load optional owner-authored premarket prompt for model strategy drafting."""
    path = PREMARKET_PROMPT_PATHS[market]
    if not path.exists():
        return {
            "present": False,
            "path": relpath(path),
            "content": "",
            "usage": "No owner prompt file found; use market data only.",
        }
    content = path.read_text(errors="replace").strip()
    compact = compact_text(content, MAX_OWNER_PROMPT_CHARS)
    return {
        "present": bool(content),
        "path": relpath(path),
        "content": compact,
        "content_chars": len(content),
        "max_chars": MAX_OWNER_PROMPT_CHARS,
        "usage": "Owner-supplied extra focus; combine with market data, do not fabricate facts.",
    }


def load_positions_tracker(market: str) -> Dict[str, Any]:
    """Load structured portfolio positions, falling back to legacy Markdown."""
    suffixes = [MARKET_CONFIG[market]["suffix"]]
    if market == "HK":
        suffixes.extend([".SZ", ".SH"])
    if POSITIONS_CURRENT.exists():
        try:
            data = json.loads(POSITIONS_CURRENT.read_text(errors="replace"))
            positions = [
                p for p in data.get("positions", [])
                if isinstance(p, dict) and any(str(p.get("symbol", "")).endswith(sfx) for sfx in suffixes)
            ]
        except Exception:
            positions = []
        if positions:
            symbols = sorted({p["symbol"] for p in positions if p.get("symbol")})
            return {
                "present": True,
                "path": relpath(POSITIONS_CURRENT),
                "legacy_markdown_path": relpath(POSITIONS_TRACKER),
                "positions": positions,
                "symbols": symbols,
                "content": compact_text(json.dumps(positions, ensure_ascii=False), MAX_POSITIONS_TRACKER_CHARS),
                "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
                "usage": f"Consider structured {market} holdings ({', '.join(symbols)}) for position-aware strategy and risk sizing.",
            }
    path = POSITIONS_TRACKER
    if not path.exists():
        return {"present": False, "path": relpath(path), "content": "", "symbols": []}
    content = path.read_text(errors="replace").strip()
    if not content:
        return {"present": False, "path": relpath(path), "content": "", "symbols": []}
    pattern = "|".join(re.escape(sfx) for sfx in suffixes)
    market_symbols = sorted(set(re.findall(rf"\b[A-Z0-9]+(?:{pattern})\b", content)))
    if not market_symbols:
        return {
            "present": False,
            "path": relpath(path),
            "content": "",
            "content_chars": len(content),
            "symbols": [],
            "usage": f"No {market} holdings found in tracker.",
        }
    compact = compact_text(content, MAX_POSITIONS_TRACKER_CHARS)
    return {
        "present": True,
        "path": relpath(path),
        "content": compact,
        "content_chars": len(content),
        "max_chars": MAX_POSITIONS_TRACKER_CHARS,
        "symbols": market_symbols,
        "usage": f"Consider listed {market} holdings ({', '.join(market_symbols)}) and key levels from compact content.",
    }


def default_market_watch(market: str, quotes: Dict[str, Dict[str, Any]], stock_screens: Dict[str, Any], medium_term_health: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create market-level watch scaffolding for the model to refine in the daily strategy."""
    cfg = MARKET_CONFIG[market]
    short_results = stock_screens.get("short_term_momentum", {}).get("results", [])
    long_results = stock_screens.get("long_term_compounder", {}).get("results", [])
    tactical = [r.get("symbol") for r in short_results if r.get("action") in ("Strong Watch", "Setup Watch") and r.get("symbol")]
    thesis = [r.get("symbol") for r in long_results if r.get("action") in ("Thesis Candidate", "DCF Candidate") and r.get("symbol")]
    avoid = [r.get("symbol") for r in short_results if r.get("action") == "Avoid Chase" and r.get("symbol")]
    benchmarks = []
    for sym in cfg["index_symbols"]:
        row = quotes.get(sym)
        benchmarks.append({
            "symbol": sym,
            "name": symbol_name(sym, row),
            "role": "risk/regime benchmark" if market == "US" else ("A股同段情绪锚" if sym.endswith((".SH", ".SZ")) else "港股科技情绪锚"),
            "quote": quote_snapshot(row, market),
            "candidate_trigger_hints": {
                "pct_change_abs_gte_medium": 1.2 if market == "US" else 1.5,
                "pct_change_abs_gte_high": 2.0 if market == "US" else 2.5,
            },
        })
    if market == "US":
        cross_asset = ["SPY.US", "QQQ.US", "TLT.US", "UUP.US", "EEM.US", "FXI.US", "IBIT.US"]
    else:
        cross_asset = ["HSTECH.HK", "000001.SH", "399001.SZ", "399006.SZ", "000300.SH", "7226.HK"]
    return {
        "required": True,
        "purpose": "盘中 live 应先跟踪市场状态和盘前假设是否成立，再跟踪个股触发器。",
        "market_questions": [
            "今天市场是 risk-on、risk-off、轮动，还是无趋势震荡？",
            "是否出现恐慌、避险、动量断裂或热点板块切换？",
            "个股波动背后对应哪条市场假设被验证或证伪？",
        ],
        "benchmarks": benchmarks,
        "cross_asset_symbols": cross_asset,
        "momentum_regime": {
            "source": "stock_screens.short_term_momentum and stock_screens.long_term_compounder",
            "tactical_watch_symbols": tactical[:8],
            "thesis_candidate_symbols": thesis[:8],
            "avoid_chase_symbols": avoid[:8],
            "watch": "盘中优先验证短线选股器高分标的是否继续扩散；若 Avoid Chase 标的领跌或高分标的失效，优先判断动量断裂/风险收缩。",
        },
        "medium_term_health": {
            "source": "medium_term_health",
            "status": (medium_term_health or {}).get("status"),
            "risk_level": (medium_term_health or {}).get("risk_level"),
            "strategy_bias": (medium_term_health or {}).get("strategy_bias"),
            "watch": "盘前先用中期健康度决定进攻/防守底色；盘中验证关键收复位和失效位。",
        },
        "strategy_authoring_requirement": {
            "daily_json_field": "market_watch",
            "must_include": ["thesis", "regime_hypotheses", "benchmarks", "sector_rotation", "momentum_regime", "medium_term_health"],
            "live_priority": "market_watch observations before monitor-level stock alerts",
        },
    }


def market_watch_symbols(data: Dict[str, Any], market: str) -> List[str]:
    watch = data.get("market_watch") if isinstance(data, dict) else {}
    symbols = []
    for item in (watch or {}).get("benchmarks", []):
        if isinstance(item, dict) and item.get("symbol"):
            symbols.append(item["symbol"])
    for sym in (watch or {}).get("cross_asset_symbols", []):
        if isinstance(sym, str):
            symbols.append(sym)
    for item in (watch or {}).get("sector_rotation", []):
        if isinstance(item, dict):
            symbols.extend(s for s in item.get("symbols", []) if isinstance(s, str))
    symbols.extend(MARKET_CONFIG[market]["index_symbols"])
    return sorted(set(symbols))


def active_market_codes_for_symbols(symbols: Iterable[str], now: Optional[dt.datetime] = None) -> set[str]:
    codes = {code for sym in symbols if (code := symbol_market_code(sym))}
    return {code for code in codes if market_code_regular_session_is_active(code, now)}


def traded_market_codes_for_symbols(symbols: Iterable[str]) -> set[str]:
    codes = {code for sym in symbols if (code := symbol_market_code(sym))}
    return {code for code in codes if market_code_is_trading_day(code)}


def display_market_scope(default_label: str, codes: set[str]) -> str:
    if codes == {"CN"}:
        return "A股"
    if codes == {"HK", "CN"}:
        return "港股/A股"
    return default_label


def default_market_watch_triggers(symbol: str, market: str) -> List[Dict[str, Any]]:
    if symbol == ".VIX.US":
        return [
            {"type": "price_above", "level": 20.0, "severity": "high", "reason": "恐慌升温/VIX突破20"},
            {"type": "pct_change_abs_gte", "level": 8.0, "severity": "medium", "reason": "波动率快速变化"},
        ]
    if symbol in ("TLT.US", "UUP.US", "IBIT.US"):
        return [{"type": "pct_change_abs_gte", "level": 1.5, "severity": "medium", "reason": "跨资产信号显著变化"}]
    return [{"type": "pct_change_abs_gte", "level": 1.5 if market == "US" else 2.0, "severity": "medium", "reason": "市场基准显著波动"}]


def should_alert_market_watch(prev: Dict[str, Any], hit: Dict[str, Any]) -> bool:
    """Determine if a market watch hit should trigger a new alert."""
    if not prev:
        return True
    prev_rank = SEVERITY_RANK.get(str(prev.get("severity", "medium")), 2)
    rank = SEVERITY_RANK.get(str(hit.get("severity", "medium")), 2)
    if rank > prev_rank:
        return True
    prev_distance = float(prev.get("max_distance") or 0)
    distance = float(hit.get("distance") or 0)
    if distance >= max(prev_distance + 0.6, prev_distance * 1.2):
        return True
    return False


def evaluate_market_watch(market: str, data: Dict[str, Any], quotes: Dict[str, Dict[str, Any]], state: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    watch = data.get("market_watch") if isinstance(data, dict) else None
    if not isinstance(watch, dict):
        return [], []
    market_state = state.setdefault("market_watch", {"hits": {}, "snapshots": 0})
    market_state["snapshots"] = int(market_state.get("snapshots") or 0) + 1
    observations = []
    repeats = []
    thesis = re.sub(r"\s+", " ", str(watch.get("thesis") or watch.get("daily_thesis") or "")).strip()
    if market_state["snapshots"] == 1 and thesis:
        bench = []
        for sym in market_watch_symbols(data, market)[:6]:
            row = quotes.get(sym)
            if row:
                bench.append(brief_quote_line(display_symbol(sym, row), row))
        observations.append("🧭 盘中市场假设跟踪\n" + f"主假设: {thesis}" + (f"\n当前锚点: {' | '.join(bench)}" if bench else ""))

    benchmark_items = watch.get("benchmarks", [])
    if not isinstance(benchmark_items, list):
        benchmark_items = []
    for item in benchmark_items:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue
        sym = item["symbol"]
        row = quotes.get(sym)
        if not row:
            continue
        triggers = item.get("triggers") if isinstance(item.get("triggers"), list) else default_market_watch_triggers(sym, market)
        hits = evaluate_details(row, triggers)
        label = display_symbol(sym, row, item)
        for hit in hits:
            key = f"{sym}:{hit['key']}"
            prev = market_state["hits"].get(key, {})
            should_alert = should_alert_market_watch(prev, hit)
            market_state["hits"][key] = {
                "message": hit["message"],
                "severity": hit["severity"],
                "first_seen_at": prev.get("first_seen_at") or state["last_run_at"],
                "last_seen_at": state["last_run_at"],
                "max_distance": max(float(prev.get("max_distance") or 0), float(hit.get("distance") or 0)),
            }
            line = f"{label}: {fmt_price(row)}｜{hit['message']}"
            if should_alert:
                observations.append("📌 市场观察触发\n" + line + (f"\n关联假设: {thesis}" if thesis else ""))
            elif prev:
                repeats.append(line)
    return observations, repeats


def build_premarket_pack(market: str) -> str:
    """Collect compact market data pack for model-driven premarket strategy drafting."""
    cfg = MARKET_CONFIG[market]
    STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
    thesis_set = set(thesis_symbols(market))
    symbols = sorted(set(cfg["default_symbols"]) | thesis_set)
    extra_symbols = [item["us_symbol"] for item in HK_OVERNIGHT_US_MAP] if market == "HK" else []
    quotes = quote(cfg["quote_core"] + symbols + extra_symbols)
    news_queries = ["US stock market premarket", "US stock futures premarket today"] if market == "US" else ["港股 盘前 恒生指数", "港股 今日 开盘 恒生科技", "中概股 隔夜 美股 金龙指数 阿里 腾讯 美团 小米"]
    news = []
    for query in news_queries:
        news.extend(news_search(query, 2))
    seen_news = set()
    news = [n for n in news if not (n in seen_news or seen_news.add(n))][:MAX_NEWS_TITLES]

    def compact_quote(sym: str) -> Dict[str, Any]:
        return quote_snapshot(quotes.get(sym), market)

    monitors = []
    for sym in symbols:
        row = quotes.get(sym)
        last = qnum(row or {}, "last") or qnum(row or {}, "last_done")
        trigger_hints = {
            "pct_change_abs_gte_medium": 5.0 if market == "HK" else 4.0,
            "pct_change_abs_gte_high": 8.0 if market == "HK" else 6.0,
        }
        if last:
            trigger_hints["price_below_medium"] = round(last * 0.95, 3)
            trigger_hints["price_above_medium"] = round(last * 1.05, 3)
        monitors.append({
            "symbol": sym,
            "name": symbol_name(sym, row),
            "source": "thesis" if sym in thesis_set else "watchlist",
            "focus": thesis_summary(sym, 90) or "市场风向/流动性监控",
            "quote": compact_quote(sym),
            "candidate_trigger_hints": trigger_hints,
        })

    screen_symbols = thesis_symbols(market)
    stock_screens = {
        "short_term_momentum": run_stock_screen(screen_symbols, "short_term_momentum", top=10),
        "long_term_compounder": run_stock_screen(screen_symbols, "long_term_compounder", top=10),
        "scanned_symbols": screen_symbols,
        "usage": "Use short_term_momentum for today's tactical watch/add candidates; use long_term_compounder for thesis/DCF candidate prioritization.",
    }
    try:
        medium_term_health = scan_market_health(market)
    except Exception as exc:
        medium_term_health = {
            "schema_version": 1,
            "market": market,
            "status": "unavailable",
            "risk_level": "unknown",
            "strategy_bias": "ignore_until_data_available",
            "error": str(exc)[:180],
        }

    pack = {
        "schema_version": 1,
        "date": market_today(market),
        "market": market,
        "generated_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "market_status": market_status(market),
        "index_quotes": {s: compact_quote(s) for s in cfg["index_symbols"]},
        "quote_interpretation_rules": quote_interpretation_rules(market),
        "news_titles": news,
        "macro_events": macro_events(market),
        "hk_overnight_us_context": hk_overnight_us_context() if market == "HK" else None,
        "owner_premarket_prompt": load_premarket_prompt(market),
        "positions_tracker": load_positions_tracker(market),
        "stock_screens": stock_screens,
        "medium_term_health": medium_term_health,
        "market_watch_template": default_market_watch(market, quotes, stock_screens, medium_term_health),
        "monitors": monitors,
        "output_strategy_path": relpath(cfg["strategy"]),
        "symbol_suffix": cfg["suffix"],
        "allowed_symbol_suffixes": market_suffixes(market),
        "model_task": "Produce today's concise strategy from this compact pack. First define market_watch: daily market thesis, medium-term market health, regime hypotheses, cross-asset/benchmark triggers, sector rotation, and stock-screener-derived momentum-regime watches. Then define monitors for stock-specific follow-up. Live cron will prioritize market_watch before individual stocks.",
        "json_requirements": {
            "required_block": "investment-system-strategy",
            "required_top_level_fields": ["date", "market", "market_watch", "monitors"],
            "market_watch_required_fields": ["thesis", "regime_hypotheses", "benchmarks", "sector_rotation", "momentum_regime", "medium_term_health"],
            "required_monitor_fields": ["symbol", "name", "focus", "triggers"],
            "allowed_trigger_types": ["pct_change_abs_gte", "pct_change_above", "pct_change_below", "price_above", "price_below"],
            "each_symbol_must_end_with_one_of": market_suffixes(market),
            "stock_specific_display": "Show symbol + name.",
        },
    }
    return json.dumps(pack, ensure_ascii=False, separators=(",", ":"))


def live_check(market: str) -> str:
    cfg = MARKET_CONFIG[market]
    text, data = load_strategy(cfg["strategy"], market)
    if data:
        monitors = data.get("monitors", [])
    else:
        syms = extract_symbols_from_strategy(text, market) or thesis_symbols(market) or cfg["default_symbols"]
        monitors = [{"symbol": s, "focus": thesis_summary(s), "triggers": trigger_set(s, None, market)} for s in syms]
    symbols = [m["symbol"] for m in monitors]
    market_symbols = market_watch_symbols(data or {}, market)
    quote_symbols = sorted(set(symbols + market_symbols))
    active_codes = active_market_codes_for_symbols(quote_symbols)
    if not active_codes:
        return "NO_REPLY"
    monitors = [m for m in monitors if symbol_market_code(m.get("symbol", "")) in active_codes]
    symbols = [m["symbol"] for m in monitors]
    market_symbols = [s for s in market_symbols if symbol_market_code(s) in active_codes]
    quote_symbols = sorted(set(symbols + market_symbols))
    if not quote_symbols:
        return "NO_REPLY"
    quotes = quote(quote_symbols)
    state = load_live_state(market)
    state["last_run_at"] = now_iso()
    state["runs"].append({
        "ts": state["last_run_at"],
        "symbols": len(symbols),
        "market_symbols": len(market_symbols),
        "active_market_codes": sorted(active_codes),
    })
    state["runs"] = state["runs"][-32:]
    alerts = []
    repeat_lines = []
    market_alerts, market_repeats = evaluate_market_watch(market, data or {}, quotes, state)
    alerts.extend(market_alerts)
    repeat_lines.extend(market_repeats[:4])
    missing_count = sum(1 for s in quote_symbols if not quotes.get(s))
    mass_missing = missing_count > 0 and missing_count / max(len(quote_symbols), 1) >= 0.5
    if mass_missing:
        alerts.append(f"⚠️ Longbridge 数据异常: {missing_count}/{len(quote_symbols)} 个观察对象无报价，本次跳过")
    for m in monitors:
        sym = m["symbol"]
        row = quotes.get(sym)
        # Normalize: strategy files may use dotless index symbols (SPX.US),
        # but Longbridge returns dotted (.SPX.US) and quote_core keys them that way.
        if not row and not sym.startswith("."):
            row = quotes.get("." + sym)
        sym_state = state["alerts"].setdefault(sym, {"hits": {}, "events": []})
        label = display_symbol(sym, row, m)
        if not row:
            if mass_missing:
                continue
            streak = sym_state.get("data_missing_streak", 0) + 1
            sym_state["data_missing_streak"] = streak
            if streak >= 2 and not sym_state.get("data_missing_reported"):
                alerts.append(f"⚠️ {label} 数据缺失(连续 {streak} 次)")
                sym_state["data_missing_reported"] = True
            continue
        sym_state["data_missing_streak"] = 0
        sym_state["data_missing_reported"] = False
        last = qnum(row, "last") or qnum(row, "last_done")
        chg = pct(row)
        sym_state["last_seen"] = {"ts": state["last_run_at"], "price": last, "change_pct": chg}
        if chg is not None:
            sym_state["max_abs_change"] = max(abs(chg), float(sym_state.get("max_abs_change") or 0))
        hits = evaluate_details(row, m.get("triggers", []))
        incremental = []
        repeated = []
        for hit in hits:
            should_alert, why = is_incremental_hit(sym_state, hit, chg, last)
            prev = sym_state["hits"].get(hit["key"], {})
            sym_state["hits"][hit["key"]] = {
                "message": hit["message"],
                "severity": hit["severity"],
                "first_seen_at": prev.get("first_seen_at") or state["last_run_at"],
                "last_seen_at": state["last_run_at"],
                "last_price": last,
                "last_change_pct": chg,
                "last_alert_price": last if should_alert else prev.get("last_alert_price") or prev.get("last_price"),
                "last_alert_change_pct": chg if should_alert else prev.get("last_alert_change_pct") or prev.get("last_change_pct"),
                "last_alert_at": state["last_run_at"] if should_alert else prev.get("last_alert_at"),
                "max_distance": max(float(prev.get("max_distance") or 0), float(hit.get("distance") or 0)),
                "alert_count": int(prev.get("alert_count") or 0) + (1 if should_alert else 0),
            }
            if should_alert:
                incremental.append(f"{why}｜{hit['message']}")
            elif prev:
                repeated.append(hit)
        if incremental:
            sym_state["events"].append({"ts": state["last_run_at"], "price": last, "change_pct": chg, "items": incremental})
            sym_state["events"] = sym_state["events"][-12:]
            first_for_symbol = len(sym_state["events"]) == 1
            focus = f"\n背景: {compact_focus(m.get('focus',''))}" if first_for_symbol and m.get("focus") else ""
            alerts.append(
                f"🚨 {label} 增量触发\n"
                f"现价: {fmt_price(row)}\n"
                f"新增: {'；'.join(incremental[:3])}\n"
                f"下一观察: {next_watch(row, m.get('triggers', []))}"
                f"{focus}"
            )
        elif repeated:
            sym_state["repeat_count"] = int(sym_state.get("repeat_count") or 0) + 1
            repeat_lines.append(brief_quote_line(label, row))
    save_live_state(market, state)
    if not alerts:
        return "NO_REPLY"
    parts = []
    if alerts:
        parts.append("\n\n".join(alerts))
    if repeat_lines:
        parts.append("重复触发简报:\n" + "\n".join(repeat_lines[:8]))
    scope = display_market_scope(cfg["cn"], active_codes) if market == "HK" else cfg["cn"]
    return f"📈 {market_today(market)} {scope}盘中播报\n\n" + "\n\n".join(parts)


def close_review(market: str) -> str:
    cfg = MARKET_CONFIG[market]
    text, data = load_strategy(cfg["strategy"], market)
    if data:
        monitors = data.get("monitors", [])
        symbols = [m["symbol"] for m in monitors]
    else:
        symbols = extract_symbols_from_strategy(text, market) or thesis_symbols(market) or cfg["default_symbols"]
        monitors = [{"symbol": s, "focus": thesis_summary(s), "triggers": trigger_set(s, None, market)} for s in symbols]
    symbols = sorted(set(symbols + cfg["index_symbols"]))
    traded_codes = traded_market_codes_for_symbols(symbols)
    if not traded_codes:
        return "NO_REPLY"
    monitors = [m for m in monitors if symbol_market_code(m.get("symbol", "")) in traded_codes]
    symbols = sorted(s for s in symbols if symbol_market_code(s) in traded_codes)
    quotes = quote(symbols)
    state = load_live_state(market)
    active_index_symbols = [s for s in cfg["index_symbols"] if symbol_market_code(s) in traded_codes]
    idx = " | ".join(f"{display_symbol(s, quotes.get(s))}: {fmt_price(quotes.get(s))}" for s in active_index_symbols if s in quotes) or "N/A"
    movers = []
    triggered = []
    quiet = 0
    missing = []
    for m in monitors[:20]:
        sym = m["symbol"]
        row = quotes.get(sym)
        label = display_symbol(sym, row, m)
        if not row:
            missing.append(label)
            continue
        chg = pct(row)
        if chg is not None:
            movers.append((abs(chg), label, fmt_price(row)))
        sym_state = state.get("alerts", {}).get(sym, {})
        events = sym_state.get("events", [])
        if events:
            first = events[0]
            last_event = events[-1]
            triggered.append(
                f"• {label}: {fmt_price(row)} | 报警 {len(events)} 次，首次 {first.get('ts','')[11:16]}，最近 {last_event.get('ts','')[11:16]}"
            )
        else:
            quiet += 1
    movers = sorted(movers, reverse=True)[:5]
    mover_lines = [f"• {sym}: {price}" for _, sym, price in movers]
    if market == "US":
        news_query = "美股 收评 标普 纳指"
    elif traded_codes == {"CN"}:
        news_query = "A股 收评 上证 深成 创业板"
    else:
        news_query = "港股 A股 收评 恒生指数 上证 深成"
    news = news_search(news_query, 3)
    
    # P2: 市场全景 — 指数 + 主题分类
    index_section = [f"• {display_symbol(s, quotes.get(s))}: {fmt_price(quotes.get(s))}" for s in active_index_symbols if s in quotes]
    thesis_syms = thesis_symbols(market)
    thesis_syms = [s for s in thesis_syms if symbol_market_code(s) in traded_codes]
    thesis_movers = [(abs(pct(quotes.get(s))), display_symbol(s, quotes.get(s)), fmt_price(quotes.get(s))) for s in thesis_syms if s in quotes and pct(quotes.get(s)) is not None]
    thesis_movers = sorted(thesis_movers, reverse=True)[:5]
    thesis_lines = [f"• {sym}: {price}" for _, sym, price in thesis_movers]
    scope = display_market_scope(cfg["cn"], traded_codes) if market == "HK" else cfg["cn"]
    
    lines = [
        f"📋 {market_today(market)} {scope}收盘复盘",
        "",
        "## 📊 市场全景",
        "",
        f"{' '.join(index_section) if index_section else '无可用指数数据'}",
        "",
        f"├ 全天异动 Top 5:",
        "\n".join(mover_lines) if mover_lines else "├ • 无可用异动数据",
        "",
        f"├ thesis 标的表现:",
        "\n".join(thesis_lines) if thesis_lines else "├ • 无 thesis 标的数据",
        "",
        "## 📰 情报回顾",
        "",
        "盘中报警回顾:",
        "\n".join(triggered[:8]) if triggered else "• 今日无增量报警",
        "",
        f"静默监控: {quiet} 个标的未产生增量报警" + (f"；数据缺失: {', '.join(missing[:5])}" if missing else ""),
        "",
        f"要闻: {'；'.join(news[:2]) if news else '无可用新闻'}",
        "",
        "📌 下一交易日策略将由盘前 cron 重新生成（含短线/中长线选股器）",
    ]
    return "\n".join(lines)



def validate_strategy_file(market: str) -> str:
    cfg = MARKET_CONFIG[market]
    text, data = load_strategy(cfg["strategy"], market)
    if not cfg["strategy"].exists():
        raise RuntimeError(f"missing strategy file: {cfg['strategy']}")
    if not data:
        raise RuntimeError("missing or invalid investment-system-strategy JSON block for today")
    if data.get("market") != market:
        raise RuntimeError("strategy market mismatch")
    if data.get("date") != market_today(market):
        raise RuntimeError("strategy date mismatch")
    market_watch = data.get("market_watch")
    if not isinstance(market_watch, dict):
        raise RuntimeError("strategy missing market_watch object")
    if not (market_watch.get("thesis") or market_watch.get("daily_thesis")):
        raise RuntimeError("market_watch missing thesis")
    benchmarks = market_watch.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise RuntimeError("market_watch benchmarks must be non-empty list")
    for b in benchmarks:
        if not isinstance(b, dict) or not b.get("symbol"):
            raise RuntimeError("each market_watch benchmark needs symbol")
        if b.get("triggers") is not None and not isinstance(b["triggers"], list):
            raise RuntimeError("market_watch benchmark triggers must be list")
    if not isinstance(market_watch.get("regime_hypotheses"), list) or not market_watch["regime_hypotheses"]:
        raise RuntimeError("market_watch regime_hypotheses must be non-empty list")
    health = market_watch.get("medium_term_health")
    if not isinstance(health, dict):
        raise RuntimeError("market_watch missing medium_term_health object")
    if not health.get("status"):
        raise RuntimeError("market_watch medium_term_health missing status")
    monitors = data.get("monitors")
    if not isinstance(monitors, list) or not monitors:
        raise RuntimeError("strategy monitors must be non-empty list")
    for m in monitors:
        if not isinstance(m, dict) or not m.get("symbol") or not m.get("triggers"):
            raise RuntimeError("each monitor needs symbol and triggers")
        if not m.get("name"):
            raise RuntimeError(f"monitor {m.get('symbol')} missing stock name")
        if not isinstance(m["triggers"], list):
            raise RuntimeError("monitor triggers must be list")
    suffixes = market_suffixes(market)
    bare = [m["symbol"] for m in monitors if not any(m["symbol"].endswith(sfx) for sfx in suffixes)]
    if bare:
        raise RuntimeError(f"symbols missing allowed suffix {suffixes}: {', '.join(bare[:8])}")
    missing_watch_text = ["市场特征", "板块", "动量", "恐慌", "risk", "Risk", "轮动", "中期健康度"]
    if not any(term in text for term in missing_watch_text):
        raise RuntimeError("strategy text must discuss market character, sector rotation, momentum, panic/risk state")
    if market == "HK":
        required_terms = ["KWEB", "BABA", "TCEHY", "MPNGY", "XIACY", "中概", "ADR", "隔夜美股", "金龙"]
        if not any(term in text for term in required_terms):
            raise RuntimeError("HK strategy missing hk_overnight_us_context discussion: must mention overnight China ADR/KWEB context")
        if not any(sfx in text for sfx in [".SZ", ".SH", "A股", "上证", "深证", "创业板", "沪深300"]):
            raise RuntimeError("HK strategy missing A-share same-session market coverage")
    return f"OK {relpath(cfg['strategy'])} monitors={len(monitors)} market_watch={len(benchmarks)}"

def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["premarket", "live", "close", "pack", "validate"]:
        sp = sub.add_parser(name)
        sp.add_argument("--market", choices=["US", "HK"], required=True)
    ns = ap.parse_args()
    try:
        if ns.cmd == "premarket":
            print(build_premarket_pack(ns.market))
        elif ns.cmd == "pack":
            print(build_premarket_pack(ns.market))
        elif ns.cmd == "validate":
            print(validate_strategy_file(ns.market))
        elif ns.cmd == "live":
            print(live_check(ns.market))
        elif ns.cmd == "close":
            print(close_review(ns.market))
        return 0
    except Exception as e:
        print(f"⚠️ NeoAlpha {ns.cmd} {ns.market} failed: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
