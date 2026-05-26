# NeoAlpha — Installation Guide

## Prerequisites

| Requirement | Version / Details |
|-------------|-------------------|
| **OpenClaw** | Latest (cron + agent support) |
| **Longbridge CLI** | Installed and authenticated, `longbridge` in PATH |
| **Python** | 3.10+ (scripted data pack, live check, close review) |
| **Disk space** | ~2MB for script output, ~100KB/day for runtime data |

Verify prerequisites:

```bash
openclaw --version
longbridge --version
python3 --version
```

## Quick Install

### 1. Copy the skill directory

Copy the NeoAlpha skill directory into your OpenClaw workspace. The local directory may remain `investment-system` for compatibility with existing commands:

```bash
cp -r investment-system/ ~/.openclaw/workspace/skills/
```

### 2. Create runtime directories

The skill writes daily strategies and live state to `memory/strategies/`:

```bash
mkdir -p ~/.openclaw/workspace/memory/strategies/portfolio
```

### 3. (Optional) Set up optional prompt and portfolio files

Copy templates to the runtime directory:

```bash
cp skills/neoalpha/templates/us-premarket-prompt.example.md memory/strategies/us-premarket-prompt.md
cp skills/neoalpha/templates/hk-premarket-prompt.example.md memory/strategies/hk-premarket-prompt.md
```

Edit prompt templates to match your current focus areas. Portfolio positions are managed through the ledger helper, not by manually editing `positions-tracker.md`.

### 4. Create your thesis tracker

Create thesis files in `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}` for stocks you want to monitor:

```bash
mkdir -p "${INVESTMENT_THESIS_DIR:-$HOME/Documents/neoalpha/thesis-tracker}"
cp skills/neoalpha/templates/thesis-template.md "${INVESTMENT_THESIS_DIR:-$HOME/Documents/neoalpha/thesis-tracker}/AAPL.US.md"
# Edit AAPL.US.md with your thesis
```

The premarket cron automatically discovers `*.US.md` files for US strategy. HK strategy discovers `*.HK.md` plus same-session A-share `*.SZ.md` / `*.SH.md` files and includes A-share index observations in `market_watch`.

## Cron Job Setup

Configure 8 cron jobs in OpenClaw. The paths below are relative to your workspace root.

### US Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-us-premarket` | `30 8 * * 1-5` | America/New_York | isolated | `skills/neoalpha/cron/market-us-premarket.md` |
| `market-us-live` | `*/30 9-15 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/neoalpha/cron/market-us-live.md` |
| `market-us-close` | `0 16 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/neoalpha/cron/market-us-close.md` |
| `market-us-session-reset` | `15 19 * * 1-5` | America/New_York | isolated | `skills/neoalpha/cron/market-us-session-reset.md` |

### HK Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-hk-premarket` | `30 8 * * 1-5` | Asia/Hong_Kong | isolated | `skills/neoalpha/cron/market-hk-premarket.md` |
| `market-hk-live` | `*/30 9-15 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/neoalpha/cron/market-hk-live.md` |
| `market-hk-close` | `0 16 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/neoalpha/cron/market-hk-close.md` |
| `market-hk-session-reset` | `15 19 * * 1-5` | Asia/Hong_Kong | isolated | `skills/neoalpha/cron/market-hk-session-reset.md` |

Example command to create a cron job:

```bash
openclaw cron add '{
  "name": "market-us-premarket",
  "schedule": {"kind": "cron", "expr": "30 8 * * 1-5", "tz": "America/New_York"},
  "payload": {"kind": "agentTurn", "message": "Read skills/neoalpha/cron/market-us-premarket.md and execute all steps."},
  "sessionTarget": "isolated",
  "delivery": {"mode": "announce"}
}'
```

> **Note**: live and close jobs share a persistent session (e.g. `session:market-us-live-<date>`) to maintain intraday context. The session-reset cron rotates the session to a new date each day.

## Verification

### 1. Test the data pack script

```bash
cd ~/.openclaw/workspace
python3 skills/neoalpha/scripts/build_us_premarket_pack.py | python3 -m json.tool | head -40
```

Expected: JSON with `market`, `date`, `index_quotes`, `monitors`, `news_titles` fields.

### 2. Manual premarket run

Trigger the US premarket cron:

```bash
openclaw cron run <market-us-premarket-job-id>
```

Check output:
- Strategy file written to `memory/strategies/us-daily.md`
- Briefing sent to configured channel

### 3. Manual live check

```bash
cd ~/.openclaw/workspace
python3 skills/neoalpha/scripts/run_us_live_check.py
```

Expected: `NO_REPLY` (no triggers hit) or incremental alert.

## Configuration Reference

### Tracking list

Edit `skills/neoalpha/tracking/us-market-assets.md` to adjust the asset universe scanned in premarket. The file defines which ETFs, indices, and macro assets are included in the premarket data pack.

### Individual thesis

Each thesis file in `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}` follows the template at `templates/thesis-template.md`. Required sections:

- `## 论点陈述` — investment thesis (extracted by script for focus field)
- Key price levels (support/resistance for trigger generation)

### Premarket prompts

Files `memory/strategies/us-premarket-prompt.md` and `memory/strategies/hk-premarket-prompt.md` contain owner-authored guidance injected into the premarket data pack. Edit these to add today-specific focus areas. The system reads them fresh each day (no archiving needed).

Premarket strategy JSON must include `market_watch` before `monitors[]`. `market_watch` is the live cron's main plan: market thesis, regime hypotheses, benchmark/cross-asset triggers, sector rotation, and momentum regime. Live cron evaluates this first and only then evaluates individual stock monitors.

### Positions tracker

Portfolio files use ledger-first storage:

```text
memory/strategies/portfolio/transactions.csv
memory/strategies/portfolio/instruments.yaml
memory/strategies/portfolio/positions-current.json
memory/strategies/positions-tracker.md
```

Only `transactions.csv` is the source of truth. Record natural-language trade descriptions with:

```bash
python3 skills/neoalpha/scripts/portfolio_ledger.py record "14.49买进1000股POET"
```

The helper rebuilds `positions-current.json` for premarket cron and regenerates `positions-tracker.md` as a human-readable compatibility file.

## Troubleshooting

| Problem | Check |
|---------|-------|
| "Longbridge quote 无返回" | Verify `longbridge` CLI works: `longbridge quote AAPL.US` |
| Premarket cron fails silently | Check the data pack output: `python3 skills/neoalpha/scripts/build_us_premarket_pack.py` |
| Strategy file has bare tickers (no `.US`) | Run `python3 skills/neoalpha/scripts/validate_us_strategy.py` — validation catches suffix errors |
| Live cron times out | Increase `timeoutSeconds` on the cron job (recommended: 240s for live) |
| Strategy appears stale | Confirm `memory/strategies/us-daily.md` has today's date in the JSON block |
| Thesis tracker not included | Verify file naming: US must be `{SYMBOL}.US.md`; HK/CN must be `{CODE}.{HK|SH|SZ}-{CompanyName}.md` in `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}` |

## Directory Structure After Install

```
workspace/
├── skills/neoalpha/            # Skill root
│   ├── SKILL.md
│   ├── INSTALLATION.md                  # This file
│   ├── cron/                            # Cron instruction files
│   │   ├── market-us-premarket.md
│   │   ├── market-us-live.md
│   │   ├── market-us-close.md
│   │   ├── market-us-session-reset.md
│   │   ├── market-hk-premarket.md
│   │   ├── market-hk-live.md
│   │   ├── market-hk-close.md
│   │   └── market-hk-session-reset.md
│   ├── scripts/                         # Python helpers
│   │   ├── market_strategy_engine.py
│   │   ├── portfolio_ledger.py
│   │   ├── screen_momentum.py
│   │   ├── screen_stocks.py
│   │   ├── build_dcf_model.py
│   │   ├── validate_dcf.py
│   │   ├── analyze_earnings_preview.py
│   │   ├── analyze_earnings_recap.py
│   │   ├── build_{us,hk}_premarket_pack.py
│   │   ├── validate_{us,hk}_strategy.py
│   │   ├── run_{us,hk}_live_check.py
│   │   └── generate_{us,hk}_close_review.py
│   ├── strategies/                      # Strategy YAML library
│   ├── templates/                       # User-editable templates
│   ├── references/                      # Analysis framework references
│   └── tracking/                        # Asset tracking list
└── memory/strategies/                   # Runtime output (gitignored)
    ├── us-daily.md                      # Daily US strategy
    ├── hk-daily.md                      # Daily HK strategy
    ├── us-premarket-prompt.md           # Optional owner prompt (US)
    ├── hk-premarket-prompt.md           # Optional owner prompt (HK)
    ├── portfolio/
    │   ├── transactions.csv             # Portfolio ledger source of truth
    │   ├── instruments.yaml             # Instrument metadata
    │   └── positions-current.json       # Generated position snapshot
    ├── positions-tracker.md             # Generated readable compatibility file
    └── us-live-state-YYYY-MM-DD.json    # Runtime alert dedupe
```

## Updating

To update the skill, replace files in `skills/neoalpha/` with the new version. Your external thesis-tracker files under `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}`, tracking list, and `memory/strategies/` runtime files are safe.

After updating, restart any affected cron sessions or wait for the next scheduled run.
