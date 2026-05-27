# Preset Screener Usage

Use `scripts/screen_stocks.py` for both short-term and long-term batch stock selection. Always make the universe explicit before running: market, named group, group file, symbol list, or thesis directory.

## Presets

- `short_term_momentum`: short-term momentum and technical setup screener for 1-4 week candidates.
- `long_term_compounder`: medium/long-term fundamental, valuation, and accumulation-quality screener for thesis and DCF candidates.

## Universe Inputs

Choose one primary universe input:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum --top 20
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market HK --preset long_term_compounder --top 20
python3 skills/neoalpha/scripts/screen_stocks.py --symbols AAPL.US,MSFT.US,NVDA.US --preset long_term_compounder --top 10
python3 skills/neoalpha/scripts/screen_stocks.py --group ai --preset short_term_momentum --top 20
python3 skills/neoalpha/scripts/screen_stocks.py --thesis-dir /path/to/thesis-tracker --market US --preset long_term_compounder --top 20
```

Market filters:

- `--market US`: `.US`
- `--market HK`: `.HK`
- `--market CN` or `--market A`: `.SH` and `.SZ`
- `--market SH`: `.SH`
- `--market SZ`: `.SZ`

## Custom Groups

Default group file:

```text
/Users/neoshi/Documents/neoalpha/symbol-groups.json
```

Override it with `--group-file /path/to/groups.json`. The JSON must be an object whose values are either arrays or objects with a `symbols` array:

```json
{
  "ai": ["NVDA.US", "AVGO.US", "300394.SZ"],
  "cn-semiconductor": {
    "symbols": ["002371.SZ", "600584.SH", "688110.SH"]
  }
}
```

Group modes:

- `--group ai`: scan the named group as the primary universe.
- `--from-thesis --market CN --group-filter cn-semiconductor`: scan thesis symbols, then keep only the group intersection.
- Repeating `--group` unions groups; repeating `--group-filter` filters by the union of those groups.

## Output Modes

Use table output for owner-facing summaries:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum --top 20
```

Use JSON output for cron, agents, and downstream parsing:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum --top 20 --json
```

For live market or short-term judgment, refresh market data in the current session:

```bash
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum --top 20 --technical-cache-hours 0 --kline-delay 0 --json
```

## Agent Routing Rules

1. If the user says "短线选股器", use `--preset short_term_momentum`.
2. If the user says "中长线选股器", "复利选股器", "thesis 候选", or "DCF 候选", use `--preset long_term_compounder`.
3. If the user names a market or sub-market, add the matching `--market`.
4. If the user names a custom pool, named theme, or self-defined group, use `--group` or `--group-filter` with the configured group file.
5. If the group file is missing or the group name is absent, report the available groups or ask for the symbol list before scanning.
