# Investment System — Installation Guide

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

Copy `investment-system/` into your OpenClaw workspace:

```bash
cp -r investment-system/ ~/.openclaw/workspace/skills/
```

### 2. Create runtime directories

The skill writes daily strategies and live state to `memory/strategies/`:

```bash
mkdir -p ~/.openclaw/workspace/memory/strategies/
```

### 3. (Optional) Set up optional prompt and positions files

Copy templates to the runtime directory:

```bash
cp skills/investment-system/templates/us-premarket-prompt.example.md memory/strategies/us-premarket-prompt.md
cp skills/investment-system/templates/hk-premarket-prompt.example.md memory/strategies/hk-premarket-prompt.md
cp skills/investment-system/templates/positions-tracker.example.md memory/strategies/positions-tracker.md
```

Edit each template to match your actual holdings and focus areas. These files are read by the premarket cron to inject owner guidance into strategy generation. If any file is missing or empty, the system silently skips it.

### 4. Create your thesis tracker

Create thesis files in `skills/investment-system/thesis-tracker/` for stocks you want to monitor:

```bash
cp skills/investment-system/templates/thesis-template.md skills/investment-system/thesis-tracker/AAPL.US.md
# Edit AAPL.US.md with your thesis
```

The premarket cron automatically discovers all `*.US.md` / `*.HK.md` files in the thesis-tracker and includes them in the daily strategy.

## Cron Job Setup

Configure 8 cron jobs in OpenClaw. The paths below are relative to your workspace root.

### US Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-us-premarket` | `30 8 * * 1-5` | America/New_York | isolated | `skills/investment-system/cron/market-us-premarket.md` |
| `market-us-live` | `*/30 9-15 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/investment-system/cron/market-us-live.md` |
| `market-us-close` | `0 16 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/investment-system/cron/market-us-close.md` |
| `market-us-session-reset` | `15 19 * * 1-5` | America/New_York | isolated | `skills/investment-system/cron/market-us-session-reset.md` |

### HK Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-hk-premarket` | `30 8 * * 1-5` | Asia/Hong_Kong | isolated | `skills/investment-system/cron/market-hk-premarket.md` |
| `market-hk-live` | `*/30 9-15 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/investment-system/cron/market-hk-live.md` |
| `market-hk-close` | `0 16 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/investment-system/cron/market-hk-close.md` |
| `market-hk-session-reset` | `15 19 * * 1-5` | Asia/Hong_Kong | isolated | `skills/investment-system/cron/market-hk-session-reset.md` |

Example command to create a cron job:

```bash
openclaw cron add '{
  "name": "market-us-premarket",
  "schedule": {"kind": "cron", "expr": "30 8 * * 1-5", "tz": "America/New_York"},
  "payload": {"kind": "agentTurn", "message": "Read skills/investment-system/cron/market-us-premarket.md and execute all steps."},
  "sessionTarget": "isolated",
  "delivery": {"mode": "announce"}
}'
```

> **Note**: live and close jobs share a persistent session (e.g. `session:market-us-live-<date>`) to maintain intraday context. The session-reset cron rotates the session to a new date each day.

## Verification

### 1. Test the data pack script

```bash
cd ~/.openclaw/workspace
python3 skills/investment-system/scripts/market_us_pack.py | python3 -m json.tool | head -40
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
python3 skills/investment-system/scripts/market_us_live.py
```

Expected: `NO_REPLY` (no triggers hit) or incremental alert.

## Configuration Reference

### Tracking list

Edit `skills/investment-system/tracking/us-market-assets.md` to adjust the asset universe scanned in premarket. The file defines which ETFs, indices, and macro assets are included in the premarket data pack.

### Individual thesis

Each thesis file in `thesis-tracker/` follows the template at `templates/thesis-template.md`. Required sections:

- `## 论点陈述` — investment thesis (extracted by script for focus field)
- Key price levels (support/resistance for trigger generation)

### Premarket prompts

Files `memory/strategies/us-premarket-prompt.md` and `memory/strategies/hk-premarket-prompt.md` contain owner-authored guidance injected into the premarket data pack. Edit these to add today-specific focus areas. The system reads them fresh each day (no archiving needed).

### Positions tracker

File `memory/strategies/positions-tracker.md` records non-Longbridge holdings. The premarket cron automatically extracts relevant holdings by market suffix (`.US` / `.HK`) and includes them in strategy generation.

## Troubleshooting

| Problem | Check |
|---------|-------|
| "Longbridge quote 无返回" | Verify `longbridge` CLI works: `longbridge quote AAPL.US` |
| Premarket cron fails silently | Check the data pack output: `python3 skills/investment-system/scripts/market_us_pack.py` |
| Strategy file has bare tickers (no `.US`) | Run `python3 skills/investment-system/scripts/market_us_validate.py` — validation catches suffix errors |
| Live cron times out | Increase `timeoutSeconds` on the cron job (recommended: 240s for live) |
| Strategy appears stale | Confirm `memory/strategies/us-daily.md` has today's date in the JSON block |
| Thesis tracker not included | Verify file naming: must be `{SYMBOL}.US.md` or `{SYMBOL}.HK.md` in `thesis-tracker/` |

## Directory Structure After Install

```
workspace/
├── skills/investment-system/            # Skill root
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
│   │   ├── proactive_trader.py
│   │   ├── momentum_scanner.py
│   │   ├── build_dcf_model.py
│   │   ├── validate_dcf.py
│   │   ├── earnings_preview.py
│   │   ├── earnings_recap.py
│   │   ├── market_{us,hk}_pack.py
│   │   ├── market_{us,hk}_validate.py
│   │   ├── market_{us,hk}_live.py
│   │   └── market_{us,hk}_close.py
│   ├── strategies/                      # Strategy YAML library
│   ├── templates/                       # User-editable templates
│   ├── references/                      # Analysis framework references
│   ├── thesis-tracker/                  # Long-term stock theses (user-maintained)
│   └── tracking/                        # Asset tracking list
└── memory/strategies/                   # Runtime output (gitignored)
    ├── us-daily.md                      # Daily US strategy
    ├── hk-daily.md                      # Daily HK strategy
    ├── us-premarket-prompt.md           # Optional owner prompt (US)
    ├── hk-premarket-prompt.md           # Optional owner prompt (HK)
    ├── positions-tracker.md             # Optional non-Longbridge positions
    └── us-live-state-YYYY-MM-DD.json    # Runtime alert dedupe
```

## Updating

To update the skill, replace files in `skills/investment-system/` with the new version. Your thesis-tracker files, tracking list, and `memory/strategies/` runtime files are safe (they are not part of the skill source).

After updating, restart any affected cron sessions or wait for the next scheduled run.
