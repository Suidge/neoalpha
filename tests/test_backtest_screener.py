import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import backtest_screener  # noqa: E402


class BacktestHelperTests(unittest.TestCase):
    def test_benchmark_symbol_mapping_uses_market_suffixes(self) -> None:
        self.assertEqual(backtest_screener.benchmark_symbol_for_suffix(".US"), "SPY.US")
        self.assertEqual(backtest_screener.benchmark_symbol_for_suffix(".HK"), "2800.HK")
        self.assertEqual(backtest_screener.benchmark_symbol_for_suffix(".SH"), "000300.SH")
        self.assertEqual(backtest_screener.benchmark_symbol_for_suffix(".SZ"), "000300.SH")

    def test_cooldown_skips_overlapping_signals(self) -> None:
        triggers = [120, 121, 124, 126, 131]
        self.assertEqual(backtest_screener.apply_cooldown(triggers, cooldown_days=5), [120, 126, 131])


if __name__ == "__main__":
    unittest.main()
