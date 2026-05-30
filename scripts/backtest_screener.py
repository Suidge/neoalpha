#!/usr/bin/env python3
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import statistics

# Ensure we can import screen_stocks
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

import screen_stocks

# Preset directories and default paths
THESIS_DIR = Path("/Users/neoshi/Documents/neoalpha/thesis-tracker")

def load_thesis_us_symbols(thesis_dir: Path) -> list[str]:
    """Load all US symbols from thesis-tracker directory filenames."""
    symbols = []
    if not thesis_dir.exists():
        print(f"[WARNING] Thesis directory {thesis_dir} does not exist.")
        return symbols
    for f in thesis_dir.glob("*.US.md"):
        # Extract the ticker before the suffix
        ticker = f.name.replace(".US.md", "")
        # Standardize representation to ticker.US
        symbols.append(f"{ticker}.US")
    return sorted(symbols)

def run_backtest_for_symbol(
    symbol: str,
    preset: dict,
    signal_filter: str,
    threshold: float,
    hold_days_list: list[int],
    lookback_days: int
) -> list[dict]:
    """Run historical sliding window backtest for a single symbol."""
    print(f"[INFO] Running backtest for {symbol}...")
    
    # Fetch enough K-lines to cover lookback_days + some indicator calculation buffers (min 120 bars)
    total_bars = lookback_days + 150
    # Use screen_stocks fetch_daily_klines
    rows = screen_stocks.fetch_daily_klines(symbol, bars=total_bars, cache_hours=12.0)
    if not rows or len(rows) < 120:
        print(f"[WARNING] Insufficient data for {symbol}: found {len(rows)} bars, need >= 120.")
        return []
    
    # Fetch benchmark K-lines for relative strength composite calculation
    suffix = screen_stocks._detect_market_suffix(symbol)
    bench_symbol = "SPY.US" if suffix == "US" else "2800.HK"
    bench_rows = screen_stocks.fetch_daily_klines(bench_symbol, bars=total_bars, cache_hours=12.0)
    bench_closes = [r["close"] for r in bench_rows] if bench_rows else None
    
    signals_triggered = []
    
    # Slide the window from bar index 120 up to the end of rows
    for t in range(120, len(rows)):
        # Extract history up to day t
        hist_rows = rows[:t+1]
        
        # Align benchmark closes by index
        hist_bench = None
        if bench_closes and len(bench_closes) >= len(rows):
            hist_bench = bench_closes[:t+1]
        
        # Calculate technical factors for this slice
        tech = screen_stocks.technical_factors(hist_rows, benchmark_closes=hist_bench)
        if not tech.get("available"):
            continue
            
        # Create a row representation for score_row with realistic momentum and volume inputs
        close_t = tech["close"]
        mom_12_1 = 0.0
        if len(hist_rows) >= 252:
            close_21 = hist_rows[-22]["close"]
            close_252 = hist_rows[-252]["close"]
            mom_12_1 = (close_21 / close_252 - 1) if close_252 else 0.0
            
        cms = max(-0.5, min(1.0, mom_12_1 * 1.2))
        stability = 0.65 if tech.get("signals", {}).get("trend_ok") else 0.15
        vam = max(-0.5, min(1.0, cms * 0.9))
        
        row_data = {
            "symbol": symbol,
            "close": close_t,
            "technical": tech,
            "cms": cms,
            "stability": stability,
            "vam": vam,
            "volume_ratio": tech["signals"]["day_volume_ratio"],
            "signals": {
                "MOM_12_1": mom_12_1
            },
            "quintile": 3,
            "vm_score": 0.0,
            "pe_rank": "3/10"
        }
        
        # Calculate scores (thesis text is bypassed for technical backtest)
        scored = screen_stocks.score_row(row_data, preset, THESIS_DIR)
        
        # Determine if signal is triggered
        triggered = False
        trigger_val = 0.0
        
        if signal_filter == "all":
            # Trigger when foundation >= min_score AND highlights >= 1
            triggered = scored["foundation_score"] >= preset.get("foundation", {}).get("min_score", 45) and scored["highlights_count"] >= 1
            trigger_val = scored["score"]
        else:
            # Trigger based on specific signal score
            sig_val = 0.0
            if signal_filter in tech:
                sig_val = tech[signal_filter]
            elif "signals" in tech and signal_filter in tech["signals"]:
                sig_val = float(tech["signals"][signal_filter])
            else:
                for c in scored.get("foundation_components", []):
                    if c["name"] == signal_filter:
                        sig_val = c["score"]
                        break
                for h in scored.get("highlight_details", []):
                    if h["name"] == signal_filter:
                        sig_val = h["score"]
                        break
            
            trigger_val = sig_val
            triggered = sig_val >= threshold
            
        if triggered:
            signal_date = hist_rows[-1]["date"]
            close_at_t = hist_rows[-1]["close"]
            
            trigger_info = {
                "symbol": symbol,
                "date": signal_date,
                "close": close_at_t,
                "trigger_value": round(trigger_val, 2),
                "foundation_score": scored["foundation_score"],
                "highlights_count": scored["highlights_count"],
                "highlights": [h["label"] for h in scored["highlights"]],
                "returns": {}
            }
            
            # Calculate future returns for each hold period
            for hold_days in hold_days_list:
                if t + hold_days < len(rows):
                    close_future = rows[t + hold_days]["close"]
                    ret = (close_future / close_at_t - 1) * 100
                    
                    # Calculate max drawdown during holding period
                    future_slice = rows[t+1 : t+hold_days+1]
                    if future_slice:
                        min_low = min(r["low"] for r in future_slice)
                        max_dd = (min_low / close_at_t - 1) * 100
                    else:
                        max_dd = 0.0
                        
                    trigger_info["returns"][hold_days] = {
                        "return": round(ret, 2),
                        "max_dd": round(max_dd, 2),
                        "future_date": rows[t + hold_days]["date"]
                    }
                else:
                    trigger_info["returns"][hold_days] = None
            
            signals_triggered.append(trigger_info)
            
    return signals_triggered

def analyze_and_print_results(all_triggers: list[dict], hold_days_list: list[int]):
    """Calculate and display statistics for the triggers."""
    if not all_triggers:
        print("\n[INFO] No signals triggered during the backtest period.")
        return
        
    print(f"\n================ BACKTEST STATISTICS (Total Triggers: {len(all_triggers)}) ================")
    
    for hold_days in hold_days_list:
        valid_returns = []
        drawdowns = []
        wins = []
        losses = []
        
        for t in all_triggers:
            ret_info = t["returns"].get(hold_days)
            if ret_info is not None:
                ret_val = ret_info["return"]
                valid_returns.append(ret_val)
                drawdowns.append(ret_info["max_dd"])
                if ret_val > 0:
                    wins.append(ret_val)
                else:
                    losses.append(ret_val)
                    
        if not valid_returns:
            print(f"\nHolding Period: {hold_days} Days — No complete trade history available yet.")
            continue
            
        hit_rate = len(wins) / len(valid_returns) * 100 if valid_returns else 0.0
        avg_gain = sum(valid_returns) / len(valid_returns) if valid_returns else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        win_loss_ratio = (avg_win / abs(avg_loss)) if avg_loss else float('inf')
        
        sum_win = sum(wins)
        sum_loss = sum(abs(l) for l in losses)
        profit_factor = sum_win / sum_loss if sum_loss else float('inf')
        
        avg_max_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0
        worst_dd = min(drawdowns) if drawdowns else 0.0
        
        print(f"\nHolding Period: {hold_days} Days (Sample Size: {len(valid_returns)} trades)")
        print(f"--------------------------------------------------")
        print(f"胜率 (Hit Rate)      : {hit_rate:.2f}%")
        print(f"平均收益 (Avg Gain)  : {avg_gain:.2f}%")
        print(f"平均盈利 (Avg Win)   : {avg_win:.2f}%")
        print(f"平均亏损 (Avg Loss)  : {avg_loss:.2f}%")
        print(f"盈亏比 (W/L Ratio)   : {win_loss_ratio:.2f}")
        print(f"利润因子 (Profit Fac): {profit_factor:.2f}")
        print(f"平均回撤 (Avg MaxDD) : {avg_max_dd:.2f}%")
        print(f"最大回撤 (Worst DD)  : {worst_dd:.2f}%")

    print("\n================ DETAILED SIGNAL TRIGGERS (Recent 20) ================")
    sorted_triggers = sorted(all_triggers, key=lambda x: x["date"])
    for t in sorted_triggers[-20:]:
        ret_strs = []
        for h in hold_days_list:
            r_info = t["returns"].get(h)
            if r_info:
                ret_strs.append(f"{h}d: {r_info['return']}% (DD:{r_info['max_dd']}%)")
            else:
                ret_strs.append(f"{h}d: N/A")
        print(f"[{t['date']}] {t['symbol']:<8} Close: {t['close']:<7.2f} (Trigger Val: {t['trigger_value']:>6}) | " + " | ".join(ret_strs) + f" | HL: {t['highlights']}")

def main():
    parser = argparse.ArgumentParser(description="Backtesting script for NeoAlpha Stock Screener")
    parser.add_argument("--symbols", help="Comma-separated symbols to backtest (e.g. IBM.US,HOOD.US,QCOM.US)")
    parser.add_argument("--from-thesis", action="store_true", help="Use symbols from thesis-tracker")
    parser.add_argument("--thesis-dir", default=str(THESIS_DIR), help="Path to thesis-tracker directory")
    parser.add_argument("--preset", default="short_term_momentum", help="Preset name or file path")
    parser.add_argument("--signal", default="all", help="Signal to backtest: 'all' or name of a component (e.g., 'tight_base_setup', 'volume_dry_pocket', 'pre_breakout_tension')")
    parser.add_argument("--threshold", type=float, default=55.0, help="Score threshold for specific signals (ignored if signal is 'all')")
    parser.add_argument("--hold-days", default="5,10,20", help="Comma-separated holding periods in days (e.g., 5,10,20)")
    parser.add_argument("--lookback-days", type=int, default=250, help="Number of historical sliding days to test")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    args = parser.parse_args()
    
    preset = screen_stocks.load_preset(args.preset)
    thesis_dir = Path(args.thesis_dir).expanduser()
    
    symbols = []
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    elif args.from_thesis:
        symbols = load_thesis_us_symbols(thesis_dir)
    else:
        symbols = ["IBM.US", "HOOD.US", "QCOM.US", "INTC.US"]
        
    if not symbols:
        print("[ERROR] No symbols to backtest.")
        sys.exit(1)
        
    hold_days_list = [int(h.strip()) for h in args.hold_days.split(",") if h.strip()]
    
    print(f"==================================================")
    print(f"NeoAlpha Historical Screener Backtest Framework")
    print(f"Preset           : {preset.get('label', preset.get('name'))}")
    print(f"Signal tested    : {args.signal} (Threshold: {args.threshold})")
    print(f"Holding periods  : {hold_days_list} days")
    print(f"Backtest window  : {args.lookback_days} trading days")
    print(f"Symbols universe : {len(symbols)} ({', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''})")
    print(f"==================================================")
    
    all_triggers = []
    for s in symbols:
        try:
            triggers = run_backtest_for_symbol(
                s, preset, args.signal, args.threshold, hold_days_list, args.lookback_days
            )
            all_triggers.extend(triggers)
        except Exception as e:
            print(f"[ERROR] Failed backtesting for {s}: {e}")
            import traceback
            traceback.print_exc()
            
    if args.json:
        output = {
            "test_config": {
                "preset": args.preset,
                "signal": args.signal,
                "threshold": args.threshold,
                "hold_days": hold_days_list,
                "lookback_days": args.lookback_days,
                "symbols": symbols
            },
            "triggers_count": len(all_triggers),
            "triggers": all_triggers
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        analyze_and_print_results(all_triggers, hold_days_list)

if __name__ == "__main__":
    main()
