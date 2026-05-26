---
name: NeoAlpha
slug: neoalpha
version: 3.2.5
description: Run quantamental stock research, thesis tracking, momentum scans, valuation workflows, portfolio ledger, and multi-market monitoring.
---

# NeoAlpha

Quantamental investing system for OpenClaw across US, HK, and CN equities. NeoAlpha combines thesis-driven fundamental research with quantitative data flows: Longbridge market data, asynchronous thesis tracking, SMAM momentum scans, DCF valuation, natural-language portfolio ledger, and automated premarket/live/close workflows.

## When to Use

Use for stock research, investment thesis creation or updates, momentum screening, valuation/modeling, portfolio review, and cron-driven market monitoring.

## Core Rules

1. **Verify every number** — use Longbridge first; use web search only as a supplement; include source dates.
2. **Route before composing** — use the most specific reference or script for the requested workflow.
3. **Use scenarios for valuation** — DCF, LBO, and earnings preview outputs need Bear / Base / Bull cases.
4. **Keep the research discipline** — facts before inference, verification before judgment, risk before return, quantified payoff.
5. **Run screeners for strategy work** — premarket strategy must incorporate short-term and long-term preset screener results.
6. **Prioritize market state intraday** — `market_watch` is the live workflow's primary object; single-stock triggers are evidence.

## Quick Reference

See [references/quick-reference.md](references/quick-reference.md) for request routing.

Common entry points:
- Thesis tracking: [references/thesis-tracker.md](references/thesis-tracker.md)
- Initiating coverage: [references/initiating-coverage.md](references/initiating-coverage.md)
- Momentum model: [references/momentum-model.md](references/momentum-model.md)
- Portfolio monitoring: [references/portfolio-monitoring.md](references/portfolio-monitoring.md)
- Architecture: [references/architecture.md](references/architecture.md)

## External Endpoints

| Service | Purpose | Auth |
|---------|---------|------|
| `longbridge` CLI | Quotes, k-line, fundamentals, consensus, events, valuation, and news | User-managed Longbridge auth |
| OpenClaw web tools | Supplemental public research when market data is incomplete | Built in |

## Data Storage

- Thesis files: `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}`
  - US: `<SYMBOL>.US.md`, for example `TLN.US.md`
  - HK/SH/SZ: `<CODE>.<MARKET>-<CompanyName>.md`, for example `0700.HK-Tencent.md`
- Daily strategies: `memory/strategies/{us,hk}-daily.md`
- Portfolio ledger: `memory/strategies/portfolio/transactions.csv` as the source of truth
- Generated portfolio snapshots: `memory/strategies/portfolio/positions-current.json` and `memory/strategies/positions-tracker.md`
- Owner prompts: `memory/strategies/{us,hk}-premarket-prompt.md`
- Skill presets and strategy YAML: `presets/*.json` and `strategies/*.yaml`

## Security and Privacy

- Do not publish personal thesis files, portfolio ledgers, strategy outputs, prompts, or generated position snapshots.
- Keep credentials in each tool's own auth store; this skill does not require checked-in tokens or API keys.
- Treat all scripts as research and monitoring helpers only. They do not place trades.

## Position Ledger Protocol

When the user describes a position change in natural language, do not hand-edit position snapshots. Record the transaction first, then continue the analysis.

```bash
python3 skills/neoalpha/scripts/portfolio_ledger.py record "<trade description>"
```

If one message contains multiple trades, split it into atomic records. If price, quantity, side, or symbol is ambiguous, ask before recording.

## Related Sibling Skills

- `longbridge` and Longbridge sibling skills for market data, news, positions, and valuation.
- `github` for GitHub operations.
