#!/usr/bin/env python3
"""Earnings Preview — 财报前瞻

Generates a pre-earnings briefing for any stock using Longbridge CLI data.
Produces structured JSON with consensus estimates, beat/miss history,
analyst sentiment, and financial context.

Usage:
  python3 analyze_earnings_preview.py <SYMBOL> [--output json|text]

Example:
  python3 analyze_earnings_preview.py AAPL.US --output json
  python3 analyze_earnings_preview.py 700.HK --output text
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
TZ = timezone(timedelta(hours=8))


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
    """Convert unix timestamp string to YYYY-MM-DD."""
    try:
        ts = int(ts_str)
        return datetime.fromtimestamp(ts, tz=TZ).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ts_str


def earnings_preview(symbol: str) -> Dict[str, Any]:
    """Generate structured earnings preview data."""
    result = {
        "symbol": symbol,
        "generated_at": datetime.now(tz=TZ).isoformat(timespec="seconds"),
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
        result["industry"] = static.get("industry")

    # 3. Consensus estimates
    consensus = safe_lb_json(["consensus", symbol], timeout=20)
    if isinstance(consensus, dict):
        details = consensus.get("list", [{}])[0].get("details", []) if consensus.get("list") else []
        estimates = {}
        for d in details:
            key = d.get("key")
            if key in ("revenue", "eps", "net_income", "ebit"):
                estimates[key] = {
                    "estimate": d.get("estimate"),
                    "name": d.get("name"),
                }
        if estimates:
            result["consensus_estimates"] = estimates

    # 4. Forecast EPS (analyst consensus for upcoming periods)
    forecast = safe_lb_json(["forecast-eps", symbol], timeout=20)
    if isinstance(forecast, dict):
        items = forecast.get("items", [])
        if items:
            upcoming = items[0]
            result["forecast_eps"] = {
                "period": f"{parse_unix_ts(upcoming.get('forecast_start_date',''))} → {parse_unix_ts(upcoming.get('forecast_end_date',''))}",
                "mean": upcoming.get("forecast_eps_mean"),
                "high": upcoming.get("forecast_eps_highest"),
                "low": upcoming.get("forecast_eps_lowest"),
                "median": upcoming.get("forecast_eps_median"),
                "institutions_total": upcoming.get("institution_total"),
            }

    # 5. Recent financials (quarterly)
    fin_report = safe_lb_json(["financial-report", symbol, "--format", "json"], timeout=25)
    if isinstance(fin_report, dict):
        flist = fin_report.get("list", {})
        income = flist.get("IS", {}).get("indicators", [])
        recent_revenue = None
        recent_net_income = None
        for ind in income:
            accounts = ind.get("accounts", [])
            name = ind.get("name", "")
            if "营业" in name or "revenue" in name.lower():
                for acc in accounts:
                    vals = acc.get("values", [])
                    if vals:
                        recent_revenue = {
                            "period": vals[0].get("period"),
                            "value": vals[0].get("value"),
                            "yoy": vals[0].get("yoy"),
                        }
                        if len(vals) > 1:
                            recent_revenue["prior_period"] = vals[1].get("value")
            if "净利" in name or "net_income" in name.lower():
                for acc in accounts:
                    vals = acc.get("values", [])
                    if vals:
                        recent_net_income = {
                            "period": vals[0].get("period"),
                            "value": vals[0].get("value"),
                            "yoy": vals[0].get("yoy"),
                        }
        result["recent_revenue"] = recent_revenue
        result["recent_net_income"] = recent_net_income

    # 6. Valuation
    valuation = safe_lb_json(["valuation", symbol], timeout=20)
    if isinstance(valuation, dict):
        pe = valuation.get("pe_ttm") or valuation.get("pe")
        pb = valuation.get("pb")
        result["valuation"] = {
            "pe_ttm": pe,
            "pb": pb,
        }

    # 7. Finance calendar (upcoming events)
    calendar = safe_lb_json(["finance-calendar", "report", "--symbol", symbol, "--format", "json"], timeout=20)
    if isinstance(calendar, dict):
        events = calendar.get("list", [])
        earnings_events = []
        for event in events:
            infos = event.get("infos", [])
            for info in infos:
                content = info.get("content", "")
                if "业绩" in content or "earnings" in content.lower() or "report" in content.lower():
                    earnings_events.append({
                        "date": event.get("date"),
                        "content": content,
                        "counter_name": info.get("counter_name"),
                    })
        if earnings_events:
            result["upcoming_earnings_events"] = earnings_events

    return result


def format_text(result: Dict[str, Any]) -> str:
    """Format preview result as readable text."""
    lines = []
    lines.append(f"🔮 {result.get('name', result['symbol'])} 财报前瞻")
    lines.append("")

    if result.get("upcoming_earnings_events"):
        ev = result["upcoming_earnings_events"][0]
        lines.append(f"财报日: {ev.get('date', '待确认')}")
    lines.append(f"当前价: {result.get('current_price', 'N/A')}")
    lines.append(f"市值: {result.get('market_cap', 'N/A')}")
    if result.get("sector"):
        lines.append(f"行业: {result.get('sector')} / {result.get('industry', '')}")
    lines.append("")

    # Consensus
    est = result.get("consensus_estimates", {})
    if est:
        lines.append("## 一致预期")
        lines.append("")
        for key in ("revenue", "eps", "ebit", "net_income"):
            if key in est:
                v = est[key]
                lines.append(f"- {v.get('name', key)}: {v.get('estimate', 'N/A')}")
        lines.append("")

    # Forecast EPS
    feps = result.get("forecast_eps", {})
    if feps:
        lines.append(f"## EPS 一致预期 (来自 {feps.get('period', 'N/A')})")
        lines.append("")
        lines.append(f"- 均值: {feps.get('mean', 'N/A')}")
        lines.append(f"- 最高: {feps.get('high', 'N/A')}")
        lines.append(f"- 最低: {feps.get('low', 'N/A')}")
        lines.append(f"- 机构数: {feps.get('institutions_total', 'N/A')}")
        lines.append("")

    # Recent financials
    rev = result.get("recent_revenue", {})
    ni = result.get("recent_net_income", {})
    if rev:
        lines.append(f"## 近期财务 (截止 {rev.get('period', 'N/A')})")
        lines.append("")
        lines.append(f"- 营收: {rev.get('value', 'N/A')} (同比: {rev.get('yoy', 'N/A')})")
        if ni:
            lines.append(f"- 净利润: {ni.get('value', 'N/A')} (同比: {ni.get('yoy', 'N/A')})")
        lines.append("")

    # Valuation
    val = result.get("valuation", {})
    if val:
        lines.append(f"## 估值")
        lines.append(f"- PE(TTM): {val.get('pe_ttm', 'N/A')}")
        lines.append(f"- PB: {val.get('pb', 'N/A')}")
        lines.append("")

    lines.append(result.get("disclaimer", ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Earnings Preview")
    parser.add_argument("symbol", help="Symbol in <CODE>.<MARKET> format, e.g. AAPL.US")
    parser.add_argument("--output", choices=["json", "text"], default="text")
    args = parser.parse_args()

    try:
        preview = earnings_preview(args.symbol)
        if args.output == "json":
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        else:
            print(format_text(preview))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()