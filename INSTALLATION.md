# NeoAlpha — Installation Guide

> [!IMPORTANT]
> **AI Agent/Automated Installation Quickstart**
> If you are an Agentic AI Coder or installation script, you can execute the following commands in sequence to perform a complete, automated installation (fully robust and resilient to your current working directory):
> ```bash
> # 1. Determine the NeoAlpha source directory
> # (If you are running in the cloned repository directory, run: export SKILL_SRC="."
#  If you are running in the workspace root and the folder is named neoalpha, run: export SKILL_SRC="skills/neoalpha")
> export SKILL_SRC="skills/neoalpha"
> 
> # 2. Copy the skill to the standard OpenClaw workspace skills directory
> mkdir -p ~/.openclaw/workspace/skills
> cp -R "$SKILL_SRC" ~/.openclaw/workspace/skills/neoalpha 2>/dev/null || true
> 
> # 3. Create portfolio and strategy runtime directories
> mkdir -p ~/.openclaw/workspace/memory/strategies/portfolio
> 
> # 4. Copy prompt templates from the standardized destination
> cp ~/.openclaw/workspace/skills/neoalpha/templates/us-premarket-prompt.example.md ~/.openclaw/workspace/memory/strategies/us-premarket-prompt.md
> cp ~/.openclaw/workspace/skills/neoalpha/templates/hk-premarket-prompt.example.md ~/.openclaw/workspace/memory/strategies/hk-premarket-prompt.md
> 
> # 5. Create the external thesis tracker and seed an example thesis
> mkdir -p ~/Documents/neoalpha/thesis-tracker
> cp ~/.openclaw/workspace/skills/neoalpha/templates/thesis-template.md ~/Documents/neoalpha/thesis-tracker/AAPL.US.md
> 
> # 6. Run the automated script from the standardized destination to register all 8 background cron jobs in OpenClaw
> # (Change --channel/--to parameters to configure Discord/Telegram/Feishu, or 'none' for local TUI only)
> python3 ~/.openclaw/workspace/skills/neoalpha/scripts/setup_cron.py --channel none --force
> ```

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

Copy the NeoAlpha skill directory into your OpenClaw workspace:

```bash
cp -R neoalpha ~/.openclaw/workspace/skills/
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

### 5. Configure Delivery Channels & Notifications (Optional)

OpenClaw natively supports delivering cron outputs to various messaging channels (such as Discord, Telegram, Feishu, and Slack) based on the `delivery` settings configured in each cron job.

- **Option A: Feishu Bot DM (Direct Messages)**:
  By default, the bundled `cron_notify.py` script can send direct messages to a Feishu user via `lark-cli`. To configure this, create a local config file `skills/neoalpha/notify-config.json` in your skill directory:
  ```json
  {
    "feishu_user_id": "ou_your_feishu_user_id_here"
  }
  ```
  *(This file is automatically ignored by git to keep your personal identifier private)*. Alternatively, you can export the `FEISHU_NOTIFY_USER_ID` environment variable.

- **Option B: Other Channels (Discord, Telegram, Slack, or Feishu Webhooks)**:
  If a Feishu user ID is **not** set, `cron_notify.py` elegantly outputs alerts directly to stdout. This allows OpenClaw's native cron engine to intercept the alert and deliver it to whatever target channel is specified in the cron job's `"delivery"` configuration block (e.g., Telegram chat, Discord channel, Slack workspace, or Feishu group).

---

## Cron Job Setup

You must configure 8 background cron jobs in OpenClaw. You can set them up automatically (recommended, especially for AI agents) or manually.

### Method 1: Automated Registration (Recommended)

The skill includes an automated Python script [setup_cron.py](scripts/setup_cron.py) to configure and register all 8 cron jobs in one go. You can specify your preferred messaging channel and target destination:

- **For Discord / Telegram / Slack / Feishu native delivery**:
  ```bash
  python3 skills/neoalpha/scripts/setup_cron.py --channel telegram --to "@your_telegram_chat_or_channel" --force
  ```
  *(Change `telegram` to `discord`, `slack`, or `feishu` as appropriate, and specify your exact target destination)*.

- **For Feishu Bot DM (Direct Messages)**:
  Configure `notify-config.json` as described in step 5, then run:
  ```bash
  python3 skills/neoalpha/scripts/setup_cron.py --channel feishu --to "user:ou_your_feishu_user_id_here" --force
  ```

- **For standard output (local terminal only / no delivery)**:
  ```bash
  python3 skills/neoalpha/scripts/setup_cron.py --channel none --force
  ```

### Method 2: Manual Registration

If you prefer to configure jobs individually, configure the following 8 cron jobs in OpenClaw (paths below are relative to your workspace root):

#### US Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-us-premarket` | `30 8 * * 1-5` | America/New_York | isolated | `skills/neoalpha/cron/market-us-premarket.md` |
| `market-us-live` | `*/30 9-15 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/neoalpha/cron/market-us-live.md` |
| `market-us-close` | `0 16 * * 1-5` | America/New_York | session:market-us-live-\<date\> | `skills/neoalpha/cron/market-us-close.md` |
| `market-us-session-reset` | `15 19 * * 1-5` | America/New_York | isolated | `skills/neoalpha/cron/market-us-session-reset.md` |

#### HK Market Jobs

| Job ID | Schedule | TZ | Session | Instruction File |
|--------|----------|-----|---------|-----------------|
| `market-hk-premarket` | `30 8 * * 1-5` | Asia/Hong_Kong | isolated | `skills/neoalpha/cron/market-hk-premarket.md` |
| `market-hk-live` | `*/30 9-15 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/neoalpha/cron/market-hk-live.md` |
| `market-hk-close` | `0 16 * * 1-5` | Asia/Hong_Kong | session:market-hk-live-\<date\> | `skills/neoalpha/cron/market-hk-close.md` |
| `market-hk-session-reset` | `15 19 * * 1-5` | Asia/Hong_Kong | isolated | `skills/neoalpha/cron/market-hk-session-reset.md` |

Example command to manually create a single cron job:

```bash
openclaw cron add '{
  "name": "market-us-premarket",
  "schedule": {"kind": "cron", "expr": "30 8 * * 1-5", "tz": "America/New_York"},
  "payload": {"kind": "agentTurn", "message": "Read skills/neoalpha/cron/market-us-premarket.md and execute all steps."},
  "sessionTarget": "isolated",
  "delivery": {"mode": "announce", "channel": "telegram", "to": "@my_channel"}
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
│   ├── notify-config.json               # Local notification settings (gitignored)
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
│   │   ├── cron_notify.py               # Bundled cron notifications dispatcher
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
