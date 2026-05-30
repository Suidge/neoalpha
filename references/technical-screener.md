# Technical Screener Layer

NeoAlpha's preset screener combines monthly SMAM momentum with a daily technical layer. The daily layer is computed locally from Longbridge OHLCV data, not from broker-side black-box screeners.

## Data Source

Primary source:

```bash
longbridge kline SYMBOL --period day --count 380 --adjust forward --format json
```

The command returns open, high, low, close, volume, and turnover fields. NeoAlpha uses OHLCV only. K-line requests are single-symbol calls, so the screener keeps them sequential by default and writes a local cache under `~/.cache/neoalpha/kline`.

Useful flags:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py \
  --from-thesis \
  --preset short_term_momentum \
  --technical-cache-hours 6 \
  --kline-delay 0.2
```

Set `--technical-cache-hours 0` to force fresh K-line data. Use this when making intraday decisions during active market hours.

### Smart Cache Bypass (v3.3.1)

To maximize real-time accuracy during active trading sessions (e.g., verifying indicator shifts immediately after an intraday sell-off), a **Smart Cache Bypass** is enforced natively:
* Whenever the active scan universe contains **fewer than 10 symbols**, the local cache is bypassed, forcing `technical-cache-hours` to `0.0`.
* This ensures instant, fresh calculations using live intraday daily bars without manually passing parameters.
* When scanning larger sets (>= 10 symbols), the user-defined cache remains active (defaulting to 6 hours) to safeguard API thresholds.

Universe filters:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market HK --preset long_term_compounder
python3 skills/neoalpha/scripts/screen_stocks.py --group ai_infra --preset short_term_momentum
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --group-filter cn_semis --preset long_term_compounder
```

`--market` supports `US/HK/CN/A/SH/SZ`. `--group` and `--group-filter` read named symbol groups from `~/Documents/neoalpha/symbol-groups.json` unless `--group-file` is provided.

## Imported Signal Families

### Trend Regime

Inspired by the Vegas / white-yellow line files. It checks:

- EMA(EMA(close, 10), 10) versus the blended 14/28/57/114 moving average.
- Slope of the trend line and multi-period yellow line.
- Price relative to EMA144/169 and EMA288/338.
- Recent and 50-day range expansion.

Use it as the first gate: strong setups should happen inside a healthy trend structure.

### Pullback Setup

Inspired by `b1选股.txt`. It scores strong-trend pullbacks with:

- Oversold J / RSI3.
- Shrinking or extremely shrinking volume.
- Small daily amplitude.
- Pullback near the white line, BBI, or yellow line.
- Recent range expansion or washout activity.
- Large recent down-volume candle filter.

Use it for 1-10 trading day watch candidates. It is an entry-timing signal, not a standalone long-term thesis.

### Single Needle Washout

Inspired by `单针选股.txt` and `单针洗盘-日线附图.txt`. It requires three conditions to fire:

- Short stochastic washout while longer stochastic location stays high.
- A real long-lower-shadow candle: lower shadow at least 1.5x the body, at least 35% of the full daily range, close in the upper half of the range, and no heavy upper-shadow rejection.
- A support touch near the white line, BBI, or yellow line.

Trend, volume shrinkage, and recent range activity are confirmation bonuses only. They must not create a single-needle score when the core stochastic washout + candle + support conditions are absent. Use it only inside a good trend regime. Without trend and volume filters, single-needle signals can select downtrend continuation.

### MACD Phase Confirmation

Inspired by `MACDX-日线附图.txt`. It checks recent DIF/DEA golden crosses and whether the MACD phase is above or below zero.

- Below-zero cross: early repair / reversal watch.
- Above-zero cross: trend continuation / main-wave confirmation.

Use it as confirmation, not as a primary screener.

### Impulse Confirmation

Inspired by `砖型图+J-日线附图.txt`. It combines a brick-style short momentum turn, J/RSI kinetic improvement, trend structure, and recent B1-like conditions.

Use it after a pullback setup appears. It is better for confirming renewed strength than for initial broad screening.

### VCP (Volatility Contraction Pattern)

Inspired by Minervini's SEPA strategy. It detects consecutive tightening pullback cycles with diminishing volume — the hallmark of supply exhaustion before a breakout.

- 3+ pullback cycles with decreasing drawdown depth.
- Volume drying up at each successive trough.
- Higher lows forming (demand stepping up).
- Current price within 5% of the breakout pivot.

Use it in Stage 2 uptrends. Best when combined with trend regime and relative strength.

### Candlestick Reversal

Classic Japanese candlestick patterns (Steve Nison). Detects bullish reversal formations near key support levels.

Recognized patterns (by reliability):

1. **Morning Star** (45 pts): 3-candle reversal with small middle body.
2. **Hammer at Support** (40 pts): Long lower shadow ≥ 2x body, near white/yellow/BBI line.
3. **Bullish Engulfing** (35 pts): Today's bullish body fully engulfs yesterday's bearish body.
4. **Doji + Confirmation** (30 pts): Doji followed by bullish confirmation candle.
5. **Piercing Line** (25 pts): Bullish candle penetrates >50% into prior bearish candle.

Bonus for volume confirmation (+15) and support proximity (+10).

### Chan Theory Divergence (缠论背驰)

Simplified implementation of 缠中说禅 divergence detection using MACD histogram area comparison. Does not implement full pen/segment/hub (笔/段/中枢) analysis.

Detects:

- **Bottom divergence**: Price makes new low but MACD negative area shrinks — trend force is exhausting.
- **Second buy point (二买)**: After a golden cross, DIF remains above DEA or quickly recovers.
- **MACD area shrinking**: Consecutive negative areas getting smaller — bearish momentum fading.

Extremely effective in A-share markets. Use inside trend regime for best results.

### Bollinger Squeeze (TTM Squeeze)

John Bollinger's Bollinger Bands combined with Keltner Channel for volatility squeeze detection (TTM Squeeze indicator).

- Bollinger Band width (BBW) in bottom 20 percentile of last 120 bars.
- Squeeze ON: Bollinger Bands contract inside Keltner Channel — extreme compression.
- Price direction above/below middle band.
- Momentum turning positive.

A squeeze fires before major moves. Direction is determined by price position relative to middle band.

### Volume-Price Divergence

Classic volume-price analysis (Granville OBV, Wyckoff theory).

- **OBV Divergence**: Price declining but OBV flat/rising — accumulation under the surface.
- **Selling Exhaustion**: Decreasing volume on down days — bears are running out of supply.
- **Healthy Volume Pattern**: Up-day volume consistently exceeds down-day volume.
- **A/D Line Rising**: Accumulation/Distribution line trending up.

### Trend Template (Minervini 8 Conditions)

Mark Minervini's Stage 2 trend template — 8 mandatory conditions for stock health:

1. Price > MA150 and Price > MA200
2. MA150 > MA200
3. MA200 rising ≥ 1 month
4. MA50 > MA150 and MA50 > MA200
5. Price > MA50
6. Price ≥ 52-week low + 30%
7. Price within 25% of 52-week high
8. RS positive (simplified: 6-month return > 0)

Score = conditions_met / 8 × 100. Used in long-term preset foundation.

### Wave Position (Stage Analysis)

Simplified Elliott Wave / Minervini Stage Analysis based on MA200 slope and price position:

- **Stage 1 (筑底)**: MA200 flat, price near MA200 → 30 pts
- **Stage 2 (上涨)**: MA200 rising, bullish MA alignment → 85-95 pts
- **Stage 3 (见顶)**: MA200 flattening, price below → 40-45 pts
- **Stage 4 (下跌)**: MA200 declining → 5-20 pts

### Relative Strength

Stock performance vs benchmark index (SPY.US / 000300.SH / 2800.HK).

Composite RS = 0.4 × RS_63d + 0.2 × RS_126d + 0.2 × RS_189d + 0.2 × RS_252d

Mapped to 0-100. Requires benchmark kline data (1-3 extra API calls per run, cached).

### Tight Base Setup (v3.3.3)

Based on Mark Minervini's VCP pivot tightening and O'Neil's tight close concepts:
* **NR7 Narrow Day**: Today's high-low range is the narrowest among the last 7 trading days.
* **ATR Compression**: 5-day ATR / 20-day ATR < 0.65 (extreme volatility squeeze).
* **Close Tightness**: Standard deviation of closing prices over the last 5 days < 1.2% of MA20 (extreme price stability).
* **Volume Extreme Drying**: 5-day average volume < 20-day average volume * 50% (supply exhausted).
* **Near Resistance**: Close >= 95% of 50-day high (tightening at the key overhead resistance).
* **Trend Healthy**: MA50 > MA150 > MA200 and MA200 is rising.
* **Inside Day**: High < prev_high and Low > prev_low.
* **Relative Strength**: Composite RS score >= 50.

Calculated as a highlight (threshold 55). Extremely reliable for predicting explosive breakouts 1-3 days in advance.

### Volume Dry Pocket (v3.3.3)

Detects quiet institutional accumulation under the surface where price remains flat but buying force builds:
* **Extreme Volume Drying**: 3-day average volume < 50-day average volume * 40%.
* **Volume Decreasing**: Volume of the last 3 days strictly declining day-by-day.
* **Price Stable**: Closing price fluctuation over the last 3 days is < 3%.
* **OBV Rising While Flat**: OBV trends up over the last 20 days but price fails to make a new 20-day high (institutional quiet buying).
* **Near 52-Week High**: Distance to 52-week high is < 25%.
* **Above MA50**: Price stays above MA50.

Calculated as a highlight (threshold 60). Designed to detect setups like QCOM at $150 or IBM before chips act.

### Pre-Breakout Tension (v3.3.3)

Captures the "fully compressed spring" setup right at the resistance pivot:
* **Near 20-Day Resistance**: Close within 3% of 20-day high.
* **Bollinger Squeezed**: Bollinger Band width rank < 25% (imminent volatility explosion).
* **Multiple Inside Days**: At least 2 inside days in the last 3 days (extremely coiled spring).
* **Volume Dry + Price Flat**: 5-day volume < MA50 volume * 70% while 5-day price range < 2%.
* **Trend Template OK**: At least 6 out of Minervini's 8 trend conditions met.
* **RS Rising**: Composite relative strength score today > 20 days ago (relative strength accelerating).

Calculated as a highlight (threshold 65). Designed to detect apexes of symmetric triangles and wedges.

### Overextension Penalty (v3.3.3)

A negative-weighted risk component (weight -25) designed to prevent chasing high momentum at the absolute peak (e.g. buying after a 20% spike):
* **MA20 Bias**: Penalty applied when price is >8% above MA20 (`penalty += min((bias_ma20 - 8) * 4, 35)`).
* **MA50 Bias**: Penalty applied when price is >15% above MA50 (`penalty += min((bias_ma50 - 15) * 3, 30)`).
* **Consecutive Up-Closes**: If consecutive up-closes >= 7, penalty is +20; if >= 5, penalty is +10.
* **High Volatility at Highs**: If price within 3% of 52-week high but ATR ratio > 1.3, penalty is +15.

## Preset Mapping (v2 Architecture)

Both presets now use a dual-layer architecture: **Foundation** (risk-control gate) + **Highlights** (opportunity detection).

### Foundation Layer

Foundation components are weighted-averaged to produce a base score (0-100). Raw highlight diagnostics are still reported below the foundation gate, but action upgrades require meeting the minimum foundation score.

`short_term_momentum` foundation (min 45 in v3.3.3):

- `trend_regime` (weight 22) — primary risk filter
- `momentum` (weight 10) — SMAM directional confirmation (reduced in v3.3.3 to avoid monthly lag)
- `relative_strength` (weight 18) — performance versus benchmark
- `liquidity_volume` (weight 12) — tradability
- `accumulation_quality` (weight 12) — trend quality and supply absorption
- `tight_base_setup` (weight 14) — forward-looking tightness quality (new in v3.3.3)
- `concept_strength` (weight 4) — theme relevance, auxiliary only
- `catalyst` (weight 4) — catalyst presence, auxiliary only
- `risk_penalty` (weight -25) — risk deduction
- `overextension_penalty` (weight -25) — penalty for high-chasing (new in v3.3.3)

`long_term_compounder` foundation (min 40):

- `fundamental_quality` (weight 25) — thesis text quality signals
- `industry_structure` (weight 15) — industry position signals
- `competitive_position` (weight 15) — moat signals
- `valuation_upside` (weight 18) — quantitative + text valuation
- `trend_template` (weight 12) — Minervini 8-condition template
- `catalyst` (weight 8) — catalyst presence
- `risk_penalty` (weight -22) — risk deduction

### Highlight Layer

Highlight signals are evaluated independently. **Any single highlight firing is enough** to flag a stock for attention.

`short_term_momentum` highlights:

| Signal | Threshold | Source |
|--------|-----------|--------|
| 🎯 单针洗盘 | 70 | `single_needle_washout` |
| 📈 MACD相位确认 | 70 | `macd_phase_confirmation` |
| 🔥 砖型反转 | 70 | `impulse_confirmation` |
| 🚀 放量突破启动 | 70 | `breakout_ignition` |
| 🔄 强势回调 | 55 | `pullback_setup` |
| 📐 VCP收缩突破 | 65 | `vcp_pattern` |
| 🕯️ K线反转形态 | 70 | `candlestick_reversal` |
| 📊 缠论背驰 | 70 | `chan_divergence` |
| 💎 布林收缩 | 65 | `bollinger_squeeze` |
| 📉 量价背离 | 70 | `volume_price_divergence` |
| 📐 窄幅收敛蓄势 | 55 | `tight_base_setup` |
| 📥 缩量机构吸筹 | 60 | `volume_dry_pocket` |
| ⚡ 突破前高张力 | 65 | `pre_breakout_tension` |

`long_term_compounder` highlights:

| Signal | Threshold | Source |
|--------|-----------|--------|
| 📐 VCP收缩突破 | 50 | `vcp_pattern` |
| 🔄 强势回调 | 45 | `pullback_setup` |
| 🌊 Stage 2 上涨阶段 | 70 | `wave_position` |
| 🏦 筹码质量 | 55 | `accumulation_quality` |
| 💎 布林收缩 | 50 | `bollinger_squeeze` |
| 📉 量价背离 | 55 | `volume_price_divergence` |
| 💪 相对强度领先 | 65 | `relative_strength` |

## Score Interpretation (v2)

### Output Format

The v2 screener outputs for each stock:

1. **Foundation Score** (0-100): Weighted average of foundation components minus risk penalties.
2. **Highlights Count**: Number of highlight signals that exceeded their thresholds.
3. **Composite Score**: `foundation_score + Σ(highlight_confidence × highlight_bonus_weight)` — used for sorting. The short-term preset uses `0.10` to keep one-off signals from overwhelming foundation quality.
4. **Action**: Matched from condition rules (see below).
5. **Triggered Highlights**: List of specific signals with confidence scores.

### Short-term Action Rules

| Condition | Label | Meaning |
|-----------|-------|---------|
| Base ≥ 68, HL ≥ 2 | **Strong Watch** | High-quality trend plus multi-signal resonance |
| Base ≥ 58, HL ≥ 1 | **Setup Watch** | Quality foundation with a clear setup |
| Base ≥ 45, HL ≥ 1 | **Alert** | Barely qualified foundation with one signal |
| Base ≥ 45 | **Base OK** | Qualified but no high-confidence setup yet |
| Base < 45 | **Avoid** | Risk control rejection |

`breakout_ignition` is designed for early, actionable range breaks that may still have weak 6-12 month momentum. In v3.3.3, it is split into a **Pre-Ignition (蓄势期)** stage (scores 45 when within 2-5% of 20-day high with Tight Base or Volume Dry triggered) and a **Confirming Ignition** stage. If the move is already extended, the signal is suppressed instead of boosting rank, because short-term high scores should represent entry opportunities rather than post-spike recognition.

### Long-term Action Rules

| Condition | Label | Meaning |
|-----------|-------|---------|
| Base ≥ 65, HL ≥ 2 | **Thesis Candidate** | Deep thesis update |
| Base ≥ 55, HL ≥ 1 | **DCF Candidate** | Valuation model needed |
| Base ≥ 40, HL ≥ 1 | **Watch + Timing** | Has timing signal |
| Base ≥ 40 | **Watchlist Only** | Wait for catalyst |
| Base < 40 | **Reject** | Skip |

### Threshold Tuning Guide

Highlight thresholds can be adjusted in the preset JSON files. Guidelines:

- **Raise threshold** (e.g., 55 → 65): Fewer but higher-quality signals. Use if getting too many false positives.
- **Lower threshold** (e.g., 60 → 50): More signals, possibly noisier. Use if missing opportunities.
- **Foundation min_score**: Raising this tightens the risk gate; lowering it lets more speculative setups through.

Recommended approach: Run with current defaults for 2-4 weeks. Track which signals led to actual trade opportunities vs. noise. Adjust thresholds based on empirical hit rate.

To test threshold changes without modifying the preset:

```bash
# View raw scores for all highlights
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --preset short_term_momentum --json | jq '.results[].highlight_details'
```

## Performance Notes

Longbridge supports batch `quote` and `calc-index`, but daily K-line history is one symbol per request. Avoid parallel bursts because the API can return `429002 api request is limited`.

Recommended defaults:

- `--kline-delay 0.2`
- `--technical-cache-hours 6` for research scans.
- `--technical-cache-hours 0` only when a fresh scan matters more than runtime.

For a thesis universe around 60 symbols, expect the daily layer to take roughly 40-60 seconds without a warm cache.

Benchmark data (for relative strength) adds 1-3 extra API calls per run — one per market appearing in the symbol list. These are cached with the same TTL as regular kline data. For a typical thesis universe spanning US + A-share + HK, this adds roughly 2-3 seconds to runtime.

## Intraday Volume Comparison (Apple-to-Apple)

When comparing today's volume against a prior session, **always compare the same time window**—never compare a partial session against a full session.

For A-share (09:30-15:00 CST), use `longbridge kline history --period 5m` to get intraday bars:

```bash
# 5m bars, UTC timestamps: 09:30 CST = 01:30 UTC
# Yesterday's first hour (09:30-10:30 CST)
longbridge kline history SYMBOL --start YYYY-MM-DD --end YYYY-MM-DD --period 5m
# Sum 01:30-02:25 UTC bars = 12 bars covering 09:30-10:30 CST
```

Python aggregation pattern:
```python
# A股: 09:30-10:30 CST = UTC 01:30-02:30 = bars at 01:30,01:35,...,02:25
first_hour_utc = [f"01:{m:02d}" for m in range(30,60)] + [f"02:{m:02d}" for m in range(0,30)]
yesterday_vol = sum(b["vol"] for b in bars if b["time"][-8:-3] in first_hour_utc)
```

**Why this matters**: The screener's daily-summary volume (tens of millions of shares) is useless intraday. Only 5m-bar aggregation gives valid same-window comparison. A common mistake is comparing a partial trading day's total vol against a prior full-day total—this will always look like "volume shrinking" and produces false signals.
