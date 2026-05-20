#!/usr/bin/env python3
"""Earnings Recap — 财报复盘

Generates a post-earnings analysis for any stock using Longbridge CLI data.
Covers actual vs estimated numbers, surprise magnitude, stock price reaction,
and financial context.

Usage:
  python3 analyze_earnings_recap.py <SYMBOL> [--output json|text]

Example:
  python3 analyze_earnings_recap.py AAPL.US --output json
  python3 analyze_earnings_recap.py 700.HK --output text
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
TZ = datetime.now().astimezone().tzinfo or None


def run(cmd: List[str], timeout: int = 35) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "").strip() if isinstance(e.stdout, str) else "", "timeout"


def lb_json(args: List[str], timeout: int = 35) -> Any:
    code, out, err = run(["longbridge", *args, "--format", "json"], timeout=timeout)
    if code != 0 or not out:
        raise RuntimeError(f"longbridge {' '.join(args)} failed: {err or out or code}")
    return json.loads(out)


def safe_lb_json(args: List[str], timeout: int = 35) -> Any:
    try:
        return lb_json(args, timeout)
    except Exception:
        return None


def parse_unix_ts(ts_str: str) -> Optional[str]:
    try:
        ts = int(ts_str)
        return datetime.fromtimestamp(ts, tz=TZ).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ts_str


def earnings_recap(symbol: str) -> Dict[str, Any]:
    """Generate structured earnings recap data."""
    result = {
        "symbol": symbol,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "disclaimer": "Research/educational output. Not financial advice.",
    }

    # 1. Quote context
    quote = safe_lb_json(["quote", symbol], timeout=15)
    if isinstance(quote, dict):
        row = quote.get("data") or quote.get("quotes") or [quote]
        row = row[0] if isinstance(row, list) else quote
        result["current_price"] = float(row.get("last_done") or row.get("last_price") or 0)
        result["market_cap"] = row.get("market_cap")
        result["change_pct"] = row.get("change_percentage")

    # 2. Static info
    static = safe_lb_json(["static", symbol], timeout=15)
    if isinstance(static, dict):
        result["name"] = static.get("name_en") or static.get("name")
        result["sector"] = static.get("sector")

    # 3. Consensus (most recent period — check if released)
    consensus = safe_lb_json(["consensus", symbol], timeout=20)
    if isinstance(consensus, dict):
        details = consensus.get("list", [{}])[0].get("details", []) if consensus.get("list") else []
        actuals = {}
        for d in details:
            key = d.get("key")
            actual = d.get("actual")
            estimate = d.get("estimate")
            if actual and estimate:
                try:
                    actual_f = float(actual)
                    est_f = float(estimate)
                    surprise_pct = ((actual_f - est_f) / abs(est_f)) * 100 if est_f != 0 else 0
                    actuals[key] = {
                        "name": d.get("name"),
                        "estimate": estimate,
                        "actual": actual,
                        "surprise_pct": round(surprise_pct, 2),
                        "is_released": d.get("is_released", False),
                    }
                except (ValueError, TypeError):
                    pass
        if actuals:
            result["actual_vs_estimate"] = actuals

    # 4. Recent financials (quarterly — last 4 quarters)
    fin_report = safe_lb_json(["financial-report", symbol, "--format", "json"], timeout=25)
    if isinstance(fin_report, dict):
        flist = fin_report.get("list", {})
        income = flist.get("IS", {}).get("indicators", [])

        def extract_trend(name_filter: str) -> List[Dict[str, Any]]:
            for ind in income:
                if name_filter in ind.get("name", "").lower():
                    accounts = ind.get("accounts", [])
                    if accounts:
                        vals = accounts[0].get("values", [])
                        return [{
                            "period": v.get("period"),
                            "value": v.get("value"),
                            "yoy": v.get("yoy"),
                        } for v in vals[:4]]
            return []

        revenue_trend = extract_trend("revenue")
        net_income_trend = extract_trend("net_income")
        if revenue_trend:
            result["revenue_trend"] = revenue_trend
        if net_income_trend:
            result["net_income_trend"] = net_income_trend

        # Gross margin trend
        for ind in income:
            name = ind.get("name", "").lower()
            if "gross" in name or "毛利" in name:
                accounts = ind.get("accounts", [])
                if accounts:
                    vals = accounts[0].get("values", [])[:4]
                    margin_trend = []
                    for v in vals:
                        val = v.get("value")
                        rev_v = None
                        for rv in revenue_trend:
                            if rv.get("period") == v.get("period"):
                                rev_v = rv.get("value")
                                break
                        if val and rev_v:
                            try:
                                margin = (float(val) / float(rev_v)) * 100
                                margin_trend.append({
                                    "period": v.get("period"),
                                    "gross_margin": round(margin, 2),
                                })
                            except (ValueError, ZeroDivisionError):
                                pass
                    if margin_trend:
                        result["gross_margin_trend"] = margin_trend
                break

    # 5. Price reaction (last 30 trading days)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
    kline = safe_lb_json(["kline", "history", symbol, "--period", "day",
                          "--start", start, "--end", end, "--format", "json"], timeout=25)
    if isinstance(kline, list) and len(kline) >= 2:
        closes = [float(r["close"]) for r in kline if isinstance(r, dict) and r.get("close")]
        volumes = [float(r["volume"]) for r in kline if isinstance(r, dict) and r.get("volume")]
        if len(closes) >= 20:
            # 5-day return
            ret_5d = ((closes[-1] / closes[-5]) - 1) * 100 if len(closes) >= 5 else None
            # 20-day return
            ret_20d = ((closes[-1] / closes[-20]) - 1) * 100 if len(closes) >= 20 else None
            # Volume vs 20-day avg
            avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else None
            vol_ratio = round(volumes[-1] / avg_vol, 2) if avg_vol and avg_vol > 0 else None

            result["price_action"] = {
                "current_price": closes[-1],
                "recent_high": max(closes[-20:]),
                "recent_low": min(closes[-20:]),
                "return_5d": round(ret_5d, 2) if ret_5d else None,
                "return_20d": round(ret_20d, 2) if ret_20d else None,
                "volume_vs_20d_avg": vol_ratio,
            }

    # 6. Valuation
    valuation = safe_lb_json(["valuation", symbol], timeout=20)
    if isinstance(valuation, dict):
        result["valuation"] = {
            "pe_ttm": valuation.get("pe_ttm") or valuation.get("pe"),
            "pb": valuation.get("pb"),
        }

    return result


def format_text(result: Dict[str, Any]) -> str:
    """Format recap result as readable text."""
    lines = []
    lines.append(f"📊 {result.get('name', result['symbol'])} 财报复盘")
    lines.append(f"生成时间: {result.get('generated_at', '')}")
    lines.append("")

    # Headline
    actuals = result.get("actual_vs_estimate", {})
    eps = actuals.get("eps", {})
    rev = actuals.get("revenue", {})
    headline_parts = []
    if eps and eps.get("is_released"):
        headline_parts.append(f"EPS: 实际 {eps.get('actual')} vs 预期 {eps.get('estimate')} ({eps.get('surprise_pct', 0):+.2f}%)")
    if rev and rev.get("is_released"):
        headline_parts.append(f"营收: 实际 {rev.get('actual')} vs 预期 {rev.get('estimate')} ({rev.get('surprise_pct', 0):+.2f}%)")

    if headline_parts:
        lines.append("## 核心数据")
        lines.append("")
        for h in headline_parts:
            lines.append(f"- {h}")
        lines.append("")

    # Current context
    pa = result.get("price_action", {})
    lines.append(f"当前价: {result.get('current_price', 'N/A')}")
    if pa:
        lines.append(f"近20日区间: {pa.get('recent_low', 'N/A')} ~ {pa.get('recent_high', 'N/A')}")
        if pa.get("return_5d") is not None:
            lines.append(f"近5日涨跌: {pa['return_5d']:+.2f}%")
        if pa.get("return_20d") is not None:
            lines.append(f"近20日涨跌: {pa['return_20d']:+.2f}%")
        if pa.get("volume_vs_20d_avg") is not None:
            lines.append(f"成交量 vs 20日均值: {pa['volume_vs_20d_avg']}x")
    lines.append("")

    # Financial trends
    rev_trend = result.get("revenue_trend", [])
    ni_trend = result.get("net_income_trend", [])
    gm_trend = result.get("gross_margin_trend", [])

    if rev_trend:
        lines.append("## 营收趋势 (近4期)")
        lines.append("")
        lines.append("| 期次 | 营收 | 同比 |")
        lines.append("|------|------|------|")
        for r in rev_trend:
            lines.append(f"| {r.get('period', 'N/A')} | {r.get('value', 'N/A')} | {r.get('yoy', 'N/A')} |")
        lines.append("")

    if gm_trend:
        lines.append("## 毛利率趋势")
        lines.append("")
        for g in gm_trend:
            lines.append(f"- {g.get('period', 'N/A')}: {g.get('gross_margin', 'N/A')}%")
        lines.append("")

    if ni_trend:
        lines.append("## 净利润趋势")
        lines.append("")
        lines.append("| 期次 | 净利润 | 同比 |")
        lines.append("|------|--------|------|")
        for n in ni_trend:
            lines.append(f"| {n.get('period', 'N/A')} | {n.get('value', 'N/A')} | {n.get('yoy', 'N/A')} |")
        lines.append("")

    val = result.get("valuation", {})
    if val:
        lines.append(f"## 估值")
        lines.append(f"- PE(TTM): {val.get('pe_ttm', 'N/A')}")
        lines.append(f"- PB: {val.get('pb', 'N/A')}")
        lines.append("")

    lines.append(result.get("disclaimer", ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Earnings Recap")
    parser.add_argument("symbol", help="Symbol in <CODE>.<MARKET> format, e.g. AAPL.US")
    parser.add_argument("--output", choices=["json", "text"], default="text")
    args = parser.parse_args()

    try:
        recap = earnings_recap(args.symbol)
        if args.output == "json":
            print(json.dumps(recap, ensure_ascii=False, indent=2))
        else:
            print(format_text(recap))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()