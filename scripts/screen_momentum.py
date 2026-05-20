#!/usr/bin/env python3
"""
Stock Momentum Scanner — 基于 Asness, Moskowitz & Pedersen (2013)
"Value and Momentum Everywhere" 论文方法论

用法:
    # 批量扫描 watchlist 动量
    python3 screen_momentum.py --symbols 300394.SZ,300502.SZ,300308.SZ,300054.SZ

    # 带 PE 估值分位的综合 VM 分数
    python3 screen_momentum.py --symbols 300394.SZ,300502.SZ --with-value

    # 扫描 thesis tracker 所有标的
    python3 screen_momentum.py --from-thesis

    # JSON 输出
    python3 screen_momentum.py --symbols AAPL.US,MSFT.US --json

依赖:
    - longbridge CLI（已安装并认证）
    - Python 3.9+
    - numpy（可选，用于更精确的统计；无 numpy 时用纯 Python）

"""

import json
import math
import subprocess
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict


# ── 信号权重（来自论文 + 实证调优） ──
SIGNAL_WEIGHTS = {
    "MOM_12_1": 0.35,   # 12-1 月动量（主信号）
    "MOM_6":    0.25,   # 6 月动量
    "MOM_3":    0.20,   # 3 月动量
    "MOM_12":   0.10,   # 完整 12 月（含最近月）
    "MOM_1":    0.10,   # 1 月动量（反转检测）
}

# 分位阈值（正态分布分位点）
QUINTILE_THRESHOLDS = {
    "Q1": 0.84,   # 强动量
    "Q2": 0.25,   # 正动量
    "Q3": -0.25,  # 中性
    "Q4": -0.84,  # 负动量
    "Q5": float("-inf"),  # 强负动量
}


def run_longbridge(cmd: str) -> str:
    """Run longbridge CLI and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[WARN] longbridge error: {result.stderr[:200]}", file=sys.stderr)
            return ""
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"[WARN] longbridge timeout: {cmd[:80]}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[WARN] longbridge exec error: {e}", file=sys.stderr)
        return ""


def get_monthly_closes(symbol: str, months_back: int = 13) -> list[float]:
    """
    拉取月线收盘价序列，返回最近 N 个月的收盘价列表（从旧到新）。
    """
    # 计算起始日期（cover 13+ months）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 31 + 15)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    output = run_longbridge(
        f"longbridge kline history {symbol} --start {start_str} --end {end_str} --period month"
    )
    if not output:
        return []

    closes = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or "Time" in line or "---" in line:
            continue
        parts = line.split("|")
        if len(parts) >= 8:
            try:
                close = float(parts[4].strip())
                closes.append(close)
            except ValueError:
                continue

    return closes  # from oldest to newest


def get_pe_rank(symbol: str) -> tuple[int, int]:
    """
    获取最新 PE 分位数据。返回 (pe_rank, total_count)。
    """
    output = run_longbridge(f"longbridge valuation-rank {symbol}")
    if not output:
        return (0, 0)

    # 取最后一行数据行
    lines = output.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line or "Date" in line or "───" in line:
            continue
        parts = line.split()
        if len(parts) >= 4:
            try:
                pe_field = parts[1]  # e.g. "68/159"
                pe_rank, total = pe_field.split("/")
                return (int(pe_rank), int(total))
            except (ValueError, IndexError):
                continue
    return (0, 0)


def calc_momentum_signals(closes: list[float]) -> dict[str, float]:
    """
    从月线收盘价序列计算 5 个动量信号。
    closes[-1] = 最近完整月, closes[-2] = 前月, ...
    返回 dict: {MOM_12_1, MOM_6, MOM_3, MOM_12, MOM_1}
    """
    n = len(closes)
    if n < 13:
        return {}

    # 索引：0 = 最旧, -1 = 最新（最近完整月 = t-1）
    # t-1 是最近完整月, t-2 是前月, ..., t-12 是 12 个月前
    p_t1  = closes[-1]   # 最近完整月
    p_t2  = closes[-2]   # 前月
    p_t3  = closes[-3]   # 3 个月前
    p_t6  = closes[-6]   # 6 个月前
    p_t12 = closes[-12]  # 12 个月前

    signals = {
        "MOM_12_1": (p_t2 / p_t12) - 1 if p_t12 > 0 else 0,  # t-2 到 t-12
        "MOM_6":    (p_t1 / p_t6) - 1  if p_t6 > 0 else 0,
        "MOM_3":    (p_t1 / p_t3) - 1  if p_t3 > 0 else 0,
        "MOM_12":   (p_t1 / p_t12) - 1 if p_t12 > 0 else 0,
        "MOM_1":    (p_t1 / p_t2) - 1  if p_t2 > 0 else 0,
    }
    return signals


def calc_volume_ratio(symbol: str) -> float:
    """
    估算近 3 月 vs 近 12 月成交量比率。
    拉取月线数据，计算近期 avg vol / 长期 avg vol。
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15 * 31)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    output = run_longbridge(
        f"longbridge kline history {symbol} --start {start_str} --end {end_str} --period month"
    )
    if not output:
        return 1.0

    volumes = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or "Time" in line or "---" in line:
            continue
        parts = line.split("|")
        if len(parts) >= 8:
            try:
                vol = float(parts[5].strip().replace(",", ""))
                volumes.append(vol)
            except ValueError:
                continue

    if len(volumes) < 13:
        return 1.0

    recent_3_avg = sum(volumes[-3:]) / 3
    all_12_avg = sum(volumes[-12:]) / 12
    if all_12_avg == 0:
        return 1.0
    return recent_3_avg / all_12_avg


def calc_cms(signals: dict[str, float], universe_stats: dict = None) -> float:
    """
    计算 Composite Momentum Score。
    如果提供 universe_stats，做截面标准化；否则用原始信号加权。
    """
    cms = 0.0
    for signal_name, weight in SIGNAL_WEIGHTS.items():
        raw = signals.get(signal_name, 0)
        if universe_stats:
            mean = universe_stats.get(signal_name, {}).get("mean", 0)
            std = universe_stats.get(signal_name, {}).get("std", 1)
            z = (raw - mean) / std if std > 0 else 0
        else:
            z = raw  # 不做标准化时直接用收益率
        cms += weight * z
    return cms


def calc_stability(signals: dict[str, float], cms: float) -> float:
    """信号一致性：多少信号与 CMS 同向。"""
    if cms == 0:
        return 0.5
    same_dir = sum(
        1 for s in signals.values()
        if (s > 0) == (cms > 0)
    )
    return same_dir / len(signals)


def calc_vam(cms: float, vol_ratio: float) -> float:
    """Volume-Adjusted Momentum。"""
    factor = 1.0 + min(0.5, max(0, vol_ratio - 1.0))
    return cms * factor


def calc_vm_score(cms: float, pe_rank: int, pe_total: int) -> float:
    """
    Value-Momentum 综合分数。
    Z_Value = -Z(PE rank)  →  PE 排名越低（越便宜），Z_Value 越高。
    """
    if pe_total == 0:
        return cms

    # PE 分位: 1 = 最便宜, pe_total = 最贵
    pe_pct = pe_rank / pe_total  # 0~1, 小=便宜

    # 映射到近似 Z-Score：分位 → Z（假设正态）
    # pct=0.10 → Z≈+1.28（便宜=正）, pct=0.90 → Z≈-1.28（贵=负）
    z_value = _pct_to_z(pe_pct, reverse=True)

    return 0.5 * cms + 0.5 * z_value


def _pct_to_z(pct: float, reverse: bool = False) -> float:
    """
    分位数 → Z 分数近似（正态分布）。
    """
    # 限制范围避免极端值
    pct = max(0.001, min(0.999, pct))
    z = _norm_inv(pct)
    return -z if reverse else z


def _norm_inv(p: float) -> float:
    """
    正态分布逆 CDF 近似（Abramowitz & Stegun 近似 26.2.23）。
    """
    if p <= 0 or p >= 1:
        return 0.0

    # Abramowitz and Stegun rational approximation
    a = [2.515517, 0.802853, 0.010328]
    b = [1.432788, 0.189269, 0.001308]
    c = [0.0] * 3

    t = math.sqrt(-2.0 * math.log(min(p, 1 - p)))
    num = a[0] + a[1] * t + a[2] * t * t
    den = 1.0 + b[0] * t + b[1] * t * t + b[2] * t * t * t
    z = t - num / den

    return -z if p < 0.5 else z


def classify_quintile(cms: float) -> str:
    """CMS → 五档分位标签。"""
    if cms > 0.84:
        return "Q1"
    elif cms > 0.25:
        return "Q2"
    elif cms >= -0.25:
        return "Q3"
    elif cms >= -0.84:
        return "Q4"
    else:
        return "Q5"


def action_recommendation(cms: float, stability: float, vam: float,
                          mom_3: float, mom_1: float) -> dict:
    """
    基于动量信号的操作建议。
    """
    # 默认
    action = "HOLD"
    level = "观望"
    detail = ""

    # 加仓条件
    if cms > 0.84 and stability >= 0.8 and vam > 0:
        action = "STRONG_ADD"
        level = "🟢 积极加仓"
        detail = "强动量 + 高一致性 + 量能配合"
    elif cms > 0.25 and stability >= 0.6 and mom_3 > 0:
        action = "MODERATE_ADD"
        level = "🟡 适度加仓"
        detail = "正动量 + 信号一致 + 近期趋势向上"
    elif cms > 0 and mom_3 > 0:
        action = "CAUTIOUS_ADD"
        level = "🔵 试探加仓"
        detail = "动量正但不够强，小仓位参与"

    # 减仓条件
    elif cms < -0.84:
        action = "EXIT"
        level = "🔴 清仓"
        detail = "强负动量信号"
    elif cms < -0.25 and stability < 0.4:
        action = "REDUCE"
        level = "🟠 大幅减仓"
        detail = "负动量 + 信号矛盾"
    elif mom_3 < 0 and mom_1 < 0:
        action = "TRIM"
        level = "🟡 小幅减仓"
        detail = "近期和最近月均转负"

    # 反转检测
    if cms > 0 and mom_3 > 0:
        # 检查是否刚从负区穿上来（需要历史数据，此处简化为当前 sign）
        pass

    return {
        "action": action,
        "level": level,
        "detail": detail,
        "cms": round(cms, 3),
        "quintile": classify_quintile(cms),
        "stability": round(stability, 2),
        "vam": round(vam, 3),
    }


def scan_symbols(symbols: list[str], with_value: bool = False) -> list[dict]:
    """
    批量扫描标的列表，返回完整的动量分析结果。
    """
    results = []
    all_signals = {}  # symbol → signals dict

    # Step 1: 拉取所有标的数据
    print(f"[INFO] Fetching data for {len(symbols)} symbols...", file=sys.stderr)
    for symbol in symbols:
        print(f"  {symbol}...", file=sys.stderr)
        closes = get_monthly_closes(symbol)
        if len(closes) < 13:
            print(f"  [WARN] {symbol}: insufficient data ({len(closes)} months)", file=sys.stderr)
            continue

        signals = calc_momentum_signals(closes)
        if not signals:
            continue

        all_signals[symbol] = signals

    if not all_signals:
        print("[ERROR] No valid data for any symbol.", file=sys.stderr)
        return []

    # Step 2: 计算截面统计量
    universe_stats = {}
    for sig_name in SIGNAL_WEIGHTS.keys():
        vals = [s[sig_name] for s in all_signals.values() if sig_name in s]
        if len(vals) < 3:
            universe_stats[sig_name] = {"mean": 0, "std": 1}
            continue
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance) if variance > 0 else 1
        universe_stats[sig_name] = {"mean": mean, "std": std}

    # Step 3: 计算每个标的的 CMS 和决策
    for symbol, signals in all_signals.items():
        cms = calc_cms(signals, universe_stats)
        stability = calc_stability(signals, cms)
        vol_ratio = calc_volume_ratio(symbol)
        vam = calc_vam(cms, vol_ratio)

        rec = action_recommendation(
            cms, stability, vam,
            signals.get("MOM_3", 0),
            signals.get("MOM_1", 0),
        )

        result = {
            "symbol": symbol,
            "signals": {k: round(v, 4) for k, v in signals.items()},
            "cms": round(cms, 3),
            "stability": round(stability, 2),
            "vam": round(vam, 3),
            "volume_ratio": round(vol_ratio, 2),
            **rec,
        }

        # 可选的 Value 信号
        if with_value:
            pe_rank, pe_total = get_pe_rank(symbol)
            vm_score = calc_vm_score(cms, pe_rank, pe_total)
            result["pe_rank"] = f"{pe_rank}/{pe_total}"
            result["vm_score"] = round(vm_score, 3)

        results.append(result)

    # 按 CMS 降序排列
    results.sort(key=lambda r: r["cms"], reverse=True)
    return results


def print_table(results: list[dict], with_value: bool = False):
    """格式化输出表格。"""
    if not results:
        print("No results.")
        return

    header = f"{'Rank':<5} {'Symbol':<14} {'CMS':>7} {'Q':<4} {'Stab':<5} {'VAM':>7} {'MOM_12_1':>8}"
    if with_value:
        header += f" {'PE_Rank':<10} {'VM_Score':>8}"
    header += f" {'Action'}"
    print(header)
    print("-" * len(header))

    for i, r in enumerate(results, 1):
        line = (
            f"{i:<5} "
            f"{r['symbol']:<14} "
            f"{r['cms']:>+7.3f} "
            f"{r['quintile']:<4} "
            f"{r['stability']:<5.2f} "
            f"{r['vam']:>+7.3f} "
            f"{r['signals'].get('MOM_12_1', 0):>+8.1%}"
        )
        if with_value:
            line += f" {r.get('pe_rank', 'N/A'):<10} {r.get('vm_score', 0):>+8.3f}"
        line += f" {r['level']}"
        print(line)

    print(f"\n共 {len(results)} 只标的完成扫描。")


def load_thesis_symbols(thesis_dir: str = None) -> list[str]:
    """
    从 proactive-trader/thesis-tracker 目录读取所有 thesis 标的。
    """
    if thesis_dir is None:
        # 尝试默认路径
        workspace = os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))
        thesis_dir = os.path.join(workspace, "skills", "investment-system", "thesis-tracker")

    symbols = []
    if not os.path.isdir(thesis_dir):
        print(f"[ERROR] Thesis directory not found: {thesis_dir}", file=sys.stderr)
        return symbols

    for fname in os.listdir(thesis_dir):
        if fname.endswith(".md") and "." in fname.replace(".md", ""):
            # 格式: <CODE>.<MARKET>.md
            symbol = fname.replace(".md", "")
            symbols.append(symbol)

    return sorted(symbols)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Stock Momentum Scanner — 基于 Asness, Moskowitz & Pedersen (2013) 方法论"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", type=str, help="逗号分隔的标的列表，如 300394.SZ,300502.SZ")
    group.add_argument("--from-thesis", action="store_true", help="扫描 thesis tracker 中所有标的")
    group.add_argument("--thesis-dir", type=str, help="指定 thesis tracker 目录路径")

    parser.add_argument("--with-value", action="store_true", help="加入 PE 估值分位，计算 VM 综合分数")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出（便于脚本处理）")
    parser.add_argument("--min-cms", type=float, default=None, help="CMS 最低阈值过滤（默认不过滤）")

    args = parser.parse_args()

    # 确定标的列表
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    elif args.from_thesis or args.thesis_dir:
        symbols = load_thesis_symbols(args.thesis_dir)
        if not symbols:
            print("[ERROR] No thesis symbols found.", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # 执行扫描
    results = scan_symbols(symbols, with_value=args.with_value)

    # 可选过滤
    if args.min_cms is not None:
        results = [r for r in results if r["cms"] >= args.min_cms]

    # 输出
    if args.json:
        output = {
            "scan_time": datetime.now().isoformat(),
            "methodology": "Asness, Moskowitz & Pedersen (2013) 12-1 Month Momentum",
            "symbols_scanned": len(symbols),
            "results": results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*80}")
        print(f"  Stock Momentum Scanner — Asness, Moskowitz & Pedersen (2013) 方法论")
        print(f"  扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        print(f"  标的数量: {len(symbols)} | 有效数据: {len(results)}")
        print(f"{'='*80}\n")
        print_table(results, with_value=args.with_value)


if __name__ == "__main__":
    main()
