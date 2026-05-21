#!/usr/bin/env python3
"""Portfolio ledger helper for investment-system.

The transaction ledger is the source of truth. Derived position snapshots and
Markdown are rebuilt from it.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "investment-system"
THESIS_DIR = SKILL / "thesis-tracker"
STRATEGY_DIR = ROOT / "memory" / "strategies"
PORTFOLIO_DIR = STRATEGY_DIR / "portfolio"
TRANSACTIONS_CSV = PORTFOLIO_DIR / "transactions.csv"
INSTRUMENTS_YAML = PORTFOLIO_DIR / "instruments.yaml"
POSITIONS_CURRENT = PORTFOLIO_DIR / "positions-current.json"
POSITIONS_TRACKER = STRATEGY_DIR / "positions-tracker.md"
TZ = dt.timezone(dt.timedelta(hours=8))

FIELDS = [
    "trade_id",
    "date",
    "account",
    "market",
    "symbol",
    "name",
    "side",
    "quantity",
    "price",
    "currency",
    "fees",
    "tax",
    "fx_rate",
    "thesis_id",
    "notes",
    "raw_text",
    "created_at",
]

MARKET_CURRENCY = {"US": "USD", "HK": "HKD", "SZ": "CNY", "SH": "CNY"}
MARKET_LABEL = {"US": "美股", "HK": "港股", "SZ": "A股", "SH": "A股"}


def today() -> str:
    return dt.datetime.now(TZ).date().isoformat()


def now_iso() -> str:
    return dt.datetime.now(TZ).isoformat(timespec="seconds")


def dec(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return Decimal(default)


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"


def qty_text(value: Decimal) -> str:
    if value == value.to_integral():
        return f"{int(value):,}"
    return f"{value.normalize():,}"


def decimal_text(value: Decimal, places: str | None = None) -> str:
    if places:
        return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))
    if value == value.to_integral():
        return str(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return format(value.normalize(), "f")


def market_from_symbol(symbol: str) -> str:
    suffix = symbol.rsplit(".", 1)[-1] if "." in symbol else ""
    if suffix in MARKET_CURRENCY:
        return suffix
    return "US"


def currency_from_symbol(symbol: str) -> str:
    return MARKET_CURRENCY.get(market_from_symbol(symbol), "USD")


def load_instruments() -> dict[str, dict[str, str]]:
    if not INSTRUMENTS_YAML.exists():
        return {}
    instruments: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in INSTRUMENTS_YAML.read_text(errors="replace").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Z0-9.]+):\s*$", line)
        if m:
            current = m.group(1)
            instruments[current] = {}
            continue
        if current and line.startswith("  "):
            kv = re.match(r"^\s+([A-Za-z_]+):\s*(.*?)\s*$", line)
            if kv:
                instruments[current][kv.group(1)] = kv.group(2).strip().strip('"')
    return instruments


def infer_symbol(raw_symbol: str, instruments: dict[str, dict[str, str]]) -> str:
    symbol = raw_symbol.strip().upper()
    if "." in symbol:
        return symbol
    for candidate in instruments:
        if candidate.split(".", 1)[0] == symbol:
            return candidate
    thesis_matches = sorted(p.stem for p in THESIS_DIR.glob(f"{symbol}.*.md"))
    if thesis_matches:
        return thesis_matches[0]
    if re.fullmatch(r"\d{4,5}", symbol):
        return f"{symbol}.HK"
    if re.fullmatch(r"\d{6}", symbol):
        return f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
    return f"{symbol}.US"


def symbol_name(symbol: str, instruments: dict[str, dict[str, str]]) -> str:
    meta = instruments.get(symbol, {})
    if meta.get("name"):
        return meta["name"]
    thesis = THESIS_DIR / f"{symbol}.md"
    if thesis.exists():
        first = thesis.read_text(errors="replace").splitlines()[:1]
        if first and first[0].startswith("# "):
            title = first[0].lstrip("# ").strip()
            title = re.sub(r"^Thesis:\s*", "", title, flags=re.I).strip()
            if title.startswith(symbol):
                title = title[len(symbol):].strip(" -:：")
            return title or symbol
    return symbol


def ensure_ledger() -> None:
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    if not TRANSACTIONS_CSV.exists():
        with TRANSACTIONS_CSV.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def read_transactions() -> list[dict[str, str]]:
    ensure_ledger()
    with TRANSACTIONS_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        return [{k: row.get(k, "") for k in FIELDS} for row in reader]


def write_transactions(rows: list[dict[str, str]]) -> None:
    ensure_ledger()
    with TRANSACTIONS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})


def next_trade_id(rows: list[dict[str, str]], date: str, symbol: str, side: str) -> str:
    prefix = f"{date}-{symbol.replace('.', '')}-{side}"
    count = sum(1 for r in rows if r.get("trade_id", "").startswith(prefix)) + 1
    return f"{prefix}-{count:03d}"


def parse_trade_text(text: str, date: str, account: str, instruments: dict[str, dict[str, str]]) -> dict[str, str]:
    upper_text = text.upper()
    clean = re.sub(r"\s+", "", upper_text)
    if re.search(r"买入|买进|加仓|补仓|建仓|开仓|重新买|买|BOUGHT|BUY", clean):
        side = "BUY"
    elif re.search(r"卖出|卖掉|全卖|出了|出掉|出清|平仓|止损|止盈|减仓|清仓|卖|抛|SOLD|SELL|STOPLOSS|STOPGAIN|TAKEPROFIT", clean):
        side = "SELL"
    else:
        raise ValueError("无法识别买入/卖出方向")

    qty_match = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)(?:股|SHARES?|SH)", clean)
    if not qty_match:
        raise ValueError("无法识别股数，例如：14.49买进1000股POET")
    quantity = qty_match.group(1).replace(",", "")

    symbol_pattern = r"[A-Z]{1,8}(?:\.[A-Z]{2})?|\d{4,6}(?:\.(?:HK|SZ|SH))?"
    symbols = re.findall(rf"(?:股|SHARES?|SH)\s*({symbol_pattern})", upper_text)
    symbols.extend(re.findall(symbol_pattern, upper_text))
    symbols.extend(
        candidate
        for candidate in instruments
        if candidate.split(".", 1)[0] in upper_text
    )
    symbols = [
        s for s in symbols
        if s not in {"BUY", "SELL", "BOUGHT", "SOLD", "SHARES", "SH"}
        and not re.fullmatch(r"\d+(?:\.\d+)?", s)
    ]
    if not symbols:
        raise ValueError("无法识别标的代码，例如：14.49买进1000股POET")
    symbol = infer_symbol(symbols[-1], instruments)

    numbers = [n.replace(",", "") for n in re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?", clean)]
    qty_value = Decimal(quantity)
    price_candidates = [n for n in numbers if Decimal(n) != qty_value]
    if not price_candidates:
        raise ValueError("无法识别成交价格")
    price = price_candidates[0]

    market = market_from_symbol(symbol)
    currency = instruments.get(symbol, {}).get("currency") or currency_from_symbol(symbol)
    name = symbol_name(symbol, instruments)
    return {
        "date": date,
        "account": account,
        "market": market,
        "symbol": symbol,
        "name": name,
        "side": side,
        "quantity": quantity,
        "price": price,
        "currency": currency,
        "fees": "0",
        "tax": "0",
        "fx_rate": "1",
        "thesis_id": symbol,
        "notes": "",
        "raw_text": text,
        "created_at": now_iso(),
    }


def append_transaction_from_text(text: str, date: str, account: str) -> dict[str, str]:
    instruments = load_instruments()
    rows = read_transactions()
    row = parse_trade_text(text, date, account, instruments)
    row["trade_id"] = next_trade_id(rows, row["date"], row["symbol"], row["side"])
    rows.append(row)
    write_transactions(rows)
    rebuild()
    return row


def rebuild() -> dict[str, Any]:
    rows = read_transactions()
    instruments = load_instruments()
    positions: dict[tuple[str, str], dict[str, Any]] = {}
    realized: dict[tuple[str, str], Decimal] = {}

    for row in rows:
        symbol = row["symbol"]
        account = row.get("account") or "main"
        key = (account, symbol)
        side = row["side"].upper()
        quantity = dec(row["quantity"])
        price = dec(row["price"])
        fees = dec(row["fees"])
        tax = dec(row["tax"])
        amount = quantity * price
        pos = positions.setdefault(key, {
            "account": account,
            "symbol": symbol,
            "name": row.get("name") or symbol_name(symbol, instruments),
            "market": row.get("market") or market_from_symbol(symbol),
            "currency": row.get("currency") or currency_from_symbol(symbol),
            "quantity": Decimal("0"),
            "cost_basis": Decimal("0"),
            "realized_pnl": Decimal("0"),
            "last_trade_date": row.get("date"),
        })
        if side == "BUY":
            pos["quantity"] += quantity
            pos["cost_basis"] += amount + fees + tax
        elif side == "SELL":
            if pos["quantity"] > 0:
                avg_cost = pos["cost_basis"] / pos["quantity"]
                cost_reduction = avg_cost * quantity
                pos["quantity"] -= quantity
                pos["cost_basis"] -= cost_reduction
                pos["realized_pnl"] += amount - fees - tax - cost_reduction
            else:
                pos["quantity"] -= quantity
                pos["realized_pnl"] += amount - fees - tax
        elif side == "DIVIDEND":
            pos["realized_pnl"] += amount
        pos["last_trade_date"] = row.get("date") or pos["last_trade_date"]
        realized[key] = pos["realized_pnl"]

    serializable = []
    for pos in positions.values():
        if pos["quantity"] == 0 and pos["cost_basis"] == 0:
            continue
        avg_cost = pos["cost_basis"] / pos["quantity"] if pos["quantity"] else Decimal("0")
        serializable.append({
            "account": pos["account"],
            "symbol": pos["symbol"],
            "name": pos["name"],
            "market": pos["market"],
            "currency": pos["currency"],
            "quantity": decimal_text(pos["quantity"]),
            "avg_cost": decimal_text(avg_cost, "0.0001"),
            "cost_basis": decimal_text(pos["cost_basis"], "0.01"),
            "realized_pnl": decimal_text(pos["realized_pnl"], "0.01"),
            "last_trade_date": pos["last_trade_date"],
            "thesis": str((THESIS_DIR / f"{pos['symbol']}.md").relative_to(ROOT)) if (THESIS_DIR / f"{pos['symbol']}.md").exists() else "",
        })
    serializable.sort(key=lambda x: (x["market"], x["symbol"]))

    output = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "source": str(TRANSACTIONS_CSV.relative_to(ROOT)),
        "positions": serializable,
    }
    POSITIONS_CURRENT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    write_markdown(output, rows)
    return output


def write_markdown(snapshot: dict[str, Any], rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for pos in snapshot["positions"]:
        grouped.setdefault(pos["market"], []).append(pos)
    lines = [
        "# 持仓记录",
        "",
        f"**最后更新**: {snapshot['generated_at']}",
        "",
        "> 自动生成文件。交易流水唯一事实来源：`memory/strategies/portfolio/transactions.csv`；不要手工编辑当前持仓表。",
        "",
    ]
    for market in ["US", "HK", "SZ", "SH"]:
        items = grouped.get(market, [])
        if not items:
            continue
        lines += [
            f"## {MARKET_LABEL.get(market, market)}",
            "",
            "| 标的 | 名称 | 方向 | 股数 | 均价 | 成本 | 已实现盈亏 |",
            "|------|------|:----:|-----:|-----:|-----:|-----:|",
        ]
        for pos in items:
            currency = pos["currency"]
            lines.append(
                f"| {pos['symbol']} | {pos['name']} | Long | {qty_text(dec(pos['quantity']))} | "
                f"{currency} {pos['avg_cost']} | {currency} {money(dec(pos['cost_basis']))} | {currency} {money(dec(pos['realized_pnl']))} |"
            )
        lines.append("")
    lines += [
        "---",
        "",
        "## 最近交易",
        "",
        "| 日期 | 标的 | 操作 | 股数 | 价格 | 金额 | 备注 |",
        "|:----:|------|:----:|-----:|-----:|-----:|------|",
    ]
    for row in rows[-20:]:
        amount = dec(row["quantity"]) * dec(row["price"])
        currency = row.get("currency") or currency_from_symbol(row["symbol"])
        sign = "+" if row["side"].upper() == "BUY" else "-"
        lines.append(
            f"| {row['date']} | {row['symbol']} {row.get('name','')} | {row['side']} | "
            f"{sign}{qty_text(dec(row['quantity']))} | {currency} {row['price']} | "
            f"{sign}{currency} {money(amount)} | {row.get('notes') or row.get('raw_text','')} |"
        )
    lines.append("")
    POSITIONS_TRACKER.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    record = sub.add_parser("record")
    record.add_argument("text", help="Natural-language trade, e.g. 14.49买进1000股POET")
    record.add_argument("--date", default=today())
    record.add_argument("--account", default="main")
    sub.add_parser("rebuild")
    ns = ap.parse_args()
    try:
        if ns.cmd == "record":
            row = append_transaction_from_text(ns.text, ns.date, ns.account)
            print(json.dumps({k: row[k] for k in FIELDS}, ensure_ascii=False, indent=2))
        elif ns.cmd == "rebuild":
            print(json.dumps(rebuild(), ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(f"portfolio_ledger failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
