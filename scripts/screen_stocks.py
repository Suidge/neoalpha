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

    scored = [score_row(row, preset, thesis_dir) for row in scan.get("results", [])]
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
