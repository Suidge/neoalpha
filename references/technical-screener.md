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

Inspired by `单针选股.txt` and `单针洗盘-日线附图.txt`. It looks for short stochastic washouts while longer stochastic location stays high.

Use it only inside a good trend regime. Without trend and volume filters, single-needle signals can select downtrend continuation.

### MACD Phase Confirmation

Inspired by `MACDX-日线附图.txt`. It checks recent DIF/DEA golden crosses and whether the MACD phase is above or below zero.

- Below-zero cross: early repair / reversal watch.
- Above-zero cross: trend continuation / main-wave confirmation.

Use it as confirmation, not as a primary screener.

### Impulse Confirmation

Inspired by `砖型图+J-日线附图.txt`. It combines a brick-style short momentum turn, J/RSI kinetic improvement, trend structure, and recent B1-like conditions.

Use it after a pullback setup appears. It is better for confirming renewed strength than for initial broad screening.

## Preset Mapping

`short_term_momentum` uses:

- `trend_regime`
- `pullback_setup`
- `single_needle_washout`
- `macd_phase_confirmation`
- `impulse_confirmation`

`long_term_compounder` uses:

- `technical_regime`
- `accumulation_quality`

Long-term screening deliberately does not treat B1, single-needle, or brick signals as company-quality factors. They only help with price structure and entry timing.

## Score Interpretation

Short-term scores are calibrated for sparse technical setups, so `70+` is already a strong watch candidate:

- `70+`: priority watch.
- `58-70`: setup watch.
- `45-58`: theme or backup lead.
- `<45`: avoid chasing.

Long-term scores are calibrated for thesis-driven screening:

- `76+`: thesis candidate.
- `66-76`: DCF or peer-comparison candidate.
- `52-66`: watchlist only.
- `<52`: reject / low priority.

For both presets, read the score with the ranking inside the scanned universe. A top-ranked stock in a narrow thesis pool can still be worth review even if the absolute score is below the strongest band.

## Performance Notes

Longbridge supports batch `quote` and `calc-index`, but daily K-line history is one symbol per request. Avoid parallel bursts because the API can return `429002 api request is limited`.

Recommended defaults:

- `--kline-delay 0.2`
- `--technical-cache-hours 6` for research scans.
- `--technical-cache-hours 0` only when a fresh scan matters more than runtime.

For a thesis universe around 60 symbols, expect the daily layer to take roughly 40-60 seconds without a warm cache.
