# Market Operations

Use this reference whenever the task involves market tape reading, short-term price action, intraday monitoring, premarket/postmarket interpretation, or time-sensitive stock analysis.

## 1. Routing

| Scenario | Use | Notes |
|----------|-----|-------|
| Any stock or market question | `longbridge` skill / CLI | Quotes, news, filings, fundamentals, valuation, flows, positions, and market status |
| NeoAlpha workflow execution | `SKILL.md` | Thesis, screeners, DCF, portfolio ledger, premarket/live/close monitoring |
| Market session checks | This reference, section 3 | US/HK/CN session state and extended-hours rules |
| Daily strategy output | `memory/strategies/{us,hk}-daily.md` | Latest premarket strategy, intraday triggers, close-review inputs |
| Owner focus prompts | `memory/strategies/{us,hk}-premarket-prompt.md` | Optional local focus areas injected into premarket packs |

## 2. Core Operating Rules

1. Read the `longbridge` skill first for stock, portfolio, or market questions.
2. For short-term tape reading, intraday analysis, or momentum scans, pull fresh data in the current session.
3. Use web search only as a supplement when Longbridge does not cover the required event or context.
4. Include the source and timestamp/date for prices, price changes, earnings, valuation, flows, and market status.
5. Before interpreting price action, identify the market session: premarket, regular session, postmarket, closed, lunch break, or cross-day.

## 3. Market Session Check

Before any tape-reading answer, run this mental checklist:

1. Record the current local time used for the analysis.
2. Identify the target market suffix: `.US`, `.HK`, `.SH`, `.SZ`.
3. Check whether the relevant market is in premarket, regular session, postmarket, closed, lunch break, or cross-day.
4. State whether the data field being used is appropriate for that session.

Baseline timezone: `Asia/Shanghai` / `Asia/Hong_Kong` / `Asia/Singapore` (UTC+8, no daylight saving time).

### US Equities

| Session | US Eastern Time | Beijing/HK Time, DST Mar-Nov | Beijing/HK Time, Standard Nov-Mar |
|---------|------------------|-------------------------------|-----------------------------------|
| Premarket | 04:00-09:30 | 16:00-21:30 | 17:00-22:30 |
| Regular | 09:30-16:00 | 21:30-04:00 next day | 22:30-05:00 next day |
| Postmarket | 16:00-20:00 | 04:00-08:00 | 05:00-09:00 |

US daylight saving time usually runs from the second Sunday in March to the first Sunday in November. During DST, Beijing/HK time is 12 hours ahead of US Eastern Time. During standard time, it is 13 hours ahead.

US DST quick reference in Beijing/HK time:

| Beijing/HK Time | US Market State |
|-----------------|-----------------|
| 21:30-04:00 | Regular session |
| 04:00-08:00 | Postmarket |
| 08:00-16:00 | Closed |
| 16:00-21:30 | Premarket |

### China A-Shares

| Session | Beijing Time |
|---------|--------------|
| Morning session | 09:30-11:30 |
| Lunch break | 11:30-13:00 |
| Afternoon session | 13:00-15:00 |

Do not treat the lunch break as continuous intraday trading.

### Hong Kong Equities

| Session | Hong Kong Time |
|---------|----------------|
| Morning session | 09:30-12:00 |
| Lunch break | 12:00-13:00 |
| Afternoon session | 13:00-16:00 |

Do not mix HK close with still-open A-share trading unless the symbols are explicitly separated by market.

### Japan and Korea

| Market | Local Open | Beijing/HK Time |
|--------|------------|-----------------|
| Nikkei / Japan | 09:00 JST | 08:00 |
| KOSPI / Korea | 09:00 KST | 08:00 |

At 08:30 HK premarket time, Japan and Korea have already traded for roughly 30 minutes, making them early Asia-Pacific sentiment inputs.

## 4. Extended-Hours Data Rules

`longbridge quote` may include `Extended Hours`, `pre_market_quote`, or `post_market_quote` fields. These can be historical extended-hours values from the previous trading day. Use them only when the current time is actually inside the corresponding US premarket or postmarket window.

Field rules:

1. `longbridge kline/quote` `close` and `prev_close` are regular-session close fields based on the US 16:00 ET close.
2. `post_market_quote` is valid for live interpretation only during US postmarket: Beijing/HK 04:00-08:00 in DST, 05:00-09:00 in standard time.
3. `pre_market_quote` is valid for live interpretation only during US premarket: Beijing/HK 16:00-21:30 in DST, 17:00-22:30 in standard time.
4. Before saying "postmarket up/down" or "premarket up/down", explicitly confirm the current time is in that session.

For live interpretation, prefer:

```bash
longbridge market-status
longbridge quote SYMBOL.US
longbridge intraday SYMBOL.US
```

## 5. Common Workflows

### Quick Market Tape Read

```bash
longbridge market-status
longbridge market-temp
longbridge quote SPY.US QQQ.US
longbridge news search "market catalyst"
```

Output should include: market session, index move, volume/volatility context, catalysts, and next levels to watch.

### Single-Stock Analysis

```bash
longbridge quote SYMBOL.MARKET
longbridge intraday SYMBOL.MARKET
longbridge kline history SYMBOL.MARKET --start YYYY-MM-DD --end YYYY-MM-DD --period day
longbridge news SYMBOL.MARKET
longbridge valuation-rank SYMBOL.MARKET
```

Recommended order: price action, volume/technical levels, catalysts, fundamentals/valuation, risks, operating plan.

### Short-Term Batch Scan

```bash
python3 skills/neoalpha/scripts/screen_stocks.py \
  --preset short_term_momentum \
  --symbols AAPL.US,NVDA.US,TSLA.US
```

Rules:

- For fewer than 10 symbols, NeoAlpha forces `technical-cache-hours=0.0`, suitable for intraday emergency or sharp-drop scans.
- For large universes, cache and serial rate limiting are allowed to avoid Longbridge `429002` rate limits.
- If the task is real-time tape reading, state whether cache was bypassed.

### Long-Term Screening

```bash
python3 skills/neoalpha/scripts/screen_stocks.py \
  --preset long_term_compounder \
  --universe thesis
```

Use this for thesis and DCF prioritization. It is not a replacement for real-time trading judgment.

### Position Changes

Do not hand-edit generated position snapshots. When the user describes a trade, record it through the ledger:

```bash
python3 skills/neoalpha/scripts/portfolio_ledger.py record "<natural-language trade description>"
```

`transactions.csv` is the source of truth. `positions-current.json` and `positions-tracker.md` are generated from it.

## 6. Cron and Strategy Files

| Job | Time | Purpose |
|-----|------|---------|
| `market-us-premarket` | US trading days 08:30 ET | Generate US premarket strategy |
| `market-us-live` | US trading days 09:00-15:00 ET | Isolated-session intraday trigger checks |
| `market-us-close` | US trading days 16:00 ET | Close review |
| `market-hk-premarket` | HK trading days 08:30 HKT | HK strategy, ADR overnight context, and early Asia inputs |
| `market-hk-live` | HK trading days 09:00-15:00 HKT | HK intraday checks; can still report A-share tape when HK is closed but CN trades |
| `market-hk-close` | HK trading days 16:00 HKT | Close review |

NeoAlpha live and close workflows filter symbols by market suffix (`.HK`, `.SH`, `.SZ`, `.US`) and should only evaluate a symbol when its market is actually trading or relevant for that close review.

## 7. Common Failure Modes

| Failure | Safeguard |
|---------|-----------|
| Treating stale US extended-hours data as live | Check current time against the premarket/postmarket window before citing it |
| Treating A-share/HK lunch break as regular intraday trading | State lunch break explicitly; do not infer continuous momentum |
| Mixing HK close with still-open A-share trading | Separate symbols by market suffix and session |
| Using cached data for live tape reading | Pull fresh data in the current session; bypass cache when needed |
| Over-focusing on a single-stock trigger | Start with `market_watch`; individual triggers are evidence |
| Reporting financial or valuation numbers without dates | Include data date, fiscal period, and pull time |
| Chasing emotional entries | State thesis, invalidation condition, stop level, and T+1/T+0 constraint before action |

## 8. Output Template

Use this order for tape or single-stock analysis:

1. Market state: current time, target market, session.
2. Fresh data: price, change, volume/liquidity, key index or peers.
3. Catalyst: news, filings, earnings, flows, or macro.
4. Judgment: trend, support/resistance, risk.
5. Operating plan: watch levels, triggers, invalidation.

For user-held positions, add position risk, T+1/T+0 constraint, and executable action window.

