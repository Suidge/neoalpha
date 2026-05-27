# Preset Screener Usage

Use `scripts/screen_stocks.py` for both short-term and long-term batch stock selection. Always make the universe explicit before running: market, named group, group file, symbol list, or thesis directory.

## Presets

- `short_term_momentum`: short-term momentum and technical setup screener for 1-4 week candidates.
- `long_term_compounder`: medium/long-term fundamental, valuation, and accumulation-quality screener for thesis and DCF candidates.

## v2 Dual-Layer Output

The screener uses a **v2 dual-layer architecture**: Foundation (risk-control gate) + Highlights (opportunity detection).

Each stock in the output includes:

1. **Foundation Score** (0-100): Weighted average of foundation components (trend, momentum, volume, etc.) minus risk penalty.
2. **Highlights Count**: Number of independent highlight signals that fired above their thresholds.
3. **Composite Score**: `foundation_score + Σ(highlight_confidence × 0.15)` — used for sorting/ranking.
4. **Action Label**: Determined by foundation score + highlights count (see Action Rules below).
5. **Triggered Highlights**: List of specific signals with emoji, name, and confidence score.

A stock must pass the foundation minimum score (35 for short-term, 40 for long-term) before highlights are evaluated. **Any single highlight firing is enough** to upgrade the action label.

## Action Rules

### Short-term `short_term_momentum`

| Condition | Label | Meaning |
|-----------|-------|---------|
| Base ≥ 55, HL ≥ 2 | **Strong Watch** | Multi-signal resonance — priority short-term candidate |
| Base ≥ 45, HL ≥ 1 | **Setup Watch** | Clear setup, await breakout/volume/catalyst confirmation |
| Base ≥ 35, HL ≥ 1 | **Alert** | Weak base but has a highlight signal worth monitoring |
| Base ≥ 35 | **Base OK** | Qualified foundation but no highlight signal yet |
| Base < 35 | **Avoid** | Risk control rejection — weak momentum/risk structure |

### Long-term `long_term_compounder`

| Condition | Label | Meaning |
|-----------|-------|---------|
| Base ≥ 65, HL ≥ 2 | **Thesis Candidate** | Worth deep thesis update and disconfirming conditions |
| Base ≥ 55, HL ≥ 1 | **DCF Candidate** | Worth valuation model or peer-comparison work |
| Base ≥ 40, HL ≥ 1 | **Watch + Timing** | Has timing signal, needs price/data/catalyst validation |
| Base ≥ 40 | **Watchlist Only** | Wait for catalyst or timing signal |
| Base < 40 | **Reject** | Low priority for medium/long-term tracking |

Use the action labels as triage labels, not buy/sell signals. For small thesis pools, relative rank (`Top 10` / `Top 20`) matters more than an absolute score cutoff.

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
~/Documents/neoalpha/symbol-groups.json
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

The `--json` output includes `architecture: "v2_foundation_highlights"` at the top level, and each result contains a `highlights` array with triggered signal details:

```json
{
  "architecture": "v2_foundation_highlights",
  "preset": "short_term_momentum",
  "results": [
    {
      "symbol": "300750.SZ",
      "name": "宁德时代",
      "foundation_score": 62.3,
      "highlights_count": 2,
      "composite_score": 79.1,
      "action": "Strong Watch",
      "highlights": [
        {"signal": "🔄 强势回调", "source": "pullback_setup", "confidence": 68},
        {"signal": "📐 VCP收缩突破", "source": "vcp_pattern", "confidence": 57}
      ],
      "foundation_details": {
        "trend_regime": 71,
        "momentum": 65,
        "liquidity_volume": 58,
        "risk_penalty": -8
      }
    }
  ]
}
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
6. For owner-facing interpretation, use the action rules above (not the old score bands) and mention the relative rank when the universe is small.
7. When presenting results, show the action label, foundation score, highlights count, and any triggered highlight signals with their emoji names.
