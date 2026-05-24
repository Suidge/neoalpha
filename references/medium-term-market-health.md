# Medium-Term Market Health

This framework converts a discretionary index-health checklist into a repeatable premarket risk backdrop. It is designed for `market_watch`, not for standalone buy/sell decisions.

## Inputs

Data source: Longbridge daily K-line OHLCV.

Required series:
- US: `.SPX.US`, `.IXIC.US`, `.DJI.US`, `SPY.US`, `QQQ.US`, `IWM.US`, `SOXX.US`
- HK: `HSI.HK`, `HSTECH.HK`, `HSCEI.HK`, `000001.SH`, `399001.SZ`, `399006.SZ`, `000300.SH`

## Signals

- `MA5/10/20/60/120/250`: trend stack and key support/reclaim levels.
- `20MA reclaim`: if an index closes below MA20, failure to reclaim within three sessions raises medium-term risk.
- `20MA slope`: upward slope means a brief break is more likely repairable; downward slope raises risk.
- `MACD`: daily and weekly DIF/DEA above zero support a healthy intermediate trend.
- `50% retracement`: breaking the midpoint of the latest 80-day swing implies the move has lost intermediate structure.
- `Key bearish candle`: the high of a recent large bearish candle is a recovery confirmation level.
- `20-day box`: recent range high/low approximates a simple consolidation zone.

## Output Status

- `healthy`: most core indexes are above MA20, MA20 is rising, MACD is constructive, and the 50% retracement holds.
- `warning`: partial breaks or mixed index behavior; favor holding and confirmation over chasing.
- `damaged`: primary indexes break medium-term structure, especially below MA20 for three sessions, below MA60, or below 50% retracement.

## Market Adaptation

US:
- Works directly on broad indexes, growth indexes, small caps, and key ETFs.
- Keep the video framework's MA20/60/120/250, but interpret MA50/200 mentally through US convention when needed.

HK:
- Must be interpreted with A-share and ADR context.
- HK index health is more gap-prone and externally driven, so the status should act as risk backdrop. Do not override local news, southbound flow, or overnight ADR signals.

## Premarket Use

`build_{us,hk}_premarket_pack.py` injects the scan as `medium_term_health`.

The model must use it in:
- `数据视角`: large-index health, key reclaim/invalidation levels.
- `market_watch.medium_term_health`: status, evidence, key levels, watch-next items.
- `作战计划`: position aggressiveness and chase discipline.

The health scan should influence risk appetite:
- `healthy`: normal execution if short-term screens confirm.
- `warning`: no aggressive chase; wait for reclaim levels.
- `damaged`: reduce risk, focus on defense and failed-break monitoring.
