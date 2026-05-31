import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import screen_stocks  # noqa: E402


def _row(date_idx: int, open_: float, high: float, low: float, close: float, volume: float) -> dict:
    return {
        "date": f"2025-01-{(date_idx % 28) + 1:02d}",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def _trend_rows(count: int = 260) -> list[dict]:
    rows = []
    price = 100.0
    for i in range(count):
        price *= 1.0018
        open_ = price * 0.997
        close = price
        rows.append(_row(i, open_, close * 1.006, open_ * 0.994, close, 1_000_000 + i * 400))
    return rows


class TechnicalFactorRiskTests(unittest.TestCase):
    def test_short_term_preset_components_are_known(self) -> None:
        preset = screen_stocks.load_preset("short_term_momentum")
        known = {
            component["name"]
            for component in preset["foundation"]["components"]
        } | {highlight["name"] for highlight in preset["highlights"]}
        row = {
            "symbol": "TEST.US",
            "technical": {name: 50 for name in known},
            "volume_ratio": 1.0,
            "signals": {"MOM_12_1": 0.1},
            "cms": 0.1,
            "stability": 0.5,
            "vam": 0.1,
            "vm_score": 0,
            "pe_rank": "3/10",
        }

        for name in known:
            screen_stocks.component_score(name, row, "", preset)

    def test_failed_breakout_distribution_risk_suppresses_breakout(self) -> None:
        rows = _trend_rows()
        prior_high = max(row["high"] for row in rows[-50:])
        prev_close = rows[-1]["close"]
        rows.append(
            _row(
                261,
                prev_close * 1.035,
                prior_high * 1.035,
                prev_close * 0.965,
                prior_high * 0.982,
                3_800_000,
            )
        )

        tech = screen_stocks.technical_factors(rows, benchmark_closes=[100 + i * 0.05 for i in range(len(rows))])

        self.assertGreaterEqual(tech["false_breakout_distribution_risk"], 60)
        self.assertEqual(tech["breakout_ignition"], 0)
        self.assertLess(tech["low_risk_entry"], 45)

    def test_low_risk_entry_detects_constructive_pullback(self) -> None:
        rows = _trend_rows()
        for idx in range(20):
            base = rows[-1]["close"] * (0.9985 if idx < 12 else 1.0008)
            volume = 650_000 - idx * 8_000
            rows.append(_row(261 + idx, base * 0.998, base * 1.006, base * 0.988, base, volume))
        last = rows[-1]["close"]
        rows.append(_row(290, last * 0.995, last * 1.012, last * 0.982, last * 1.006, 520_000))

        tech = screen_stocks.technical_factors(rows, benchmark_closes=[100 + i * 0.03 for i in range(len(rows))])

        self.assertGreaterEqual(tech["low_risk_entry"], 60)
        self.assertLess(tech["false_breakout_distribution_risk"], 35)
        self.assertLess(tech["overextension_penalty"], 25)

    def test_market_regime_scores_benchmark_trend(self) -> None:
        rows = _trend_rows()
        strong_benchmark = [100 + i * 0.25 for i in range(len(rows))]
        weak_benchmark = [180 - i * 0.18 for i in range(len(rows))]

        strong = screen_stocks.technical_factors(rows, benchmark_closes=strong_benchmark)
        weak = screen_stocks.technical_factors(rows, benchmark_closes=weak_benchmark)

        self.assertGreaterEqual(strong["market_regime"], 75)
        self.assertLessEqual(weak["market_regime"], 35)


if __name__ == "__main__":
    unittest.main()
