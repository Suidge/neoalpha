# Market US Session Reset

Run at 19:15 America/New_York on US market weekdays.

## Execute

Run this as one shell block so variables stay in scope:

```bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME}"
DATE=$(TZ='America/New_York' python3 -c "
from datetime import datetime, timedelta
d = datetime.now().date()
while True:
    d = d + timedelta(days=1)
    if d.weekday() < 5:
        print(d.isoformat())
        break
")

LIVE_JOB_ID=$(HOME="$OPENCLAW_HOME" openclaw cron list --json | python3 -c 'import json,sys; jobs=json.load(sys.stdin).get("jobs", []); print(next(j["id"] for j in jobs if j.get("name")=="market-us-live"))')
CLOSE_JOB_ID=$(HOME="$OPENCLAW_HOME" openclaw cron list --json | python3 -c 'import json,sys; jobs=json.load(sys.stdin).get("jobs", []); print(next(j["id"] for j in jobs if j.get("name")=="market-us-close"))')

HOME="$OPENCLAW_HOME" openclaw cron edit "$LIVE_JOB_ID" --session "session:market-us-live-$DATE"
HOME="$OPENCLAW_HOME" openclaw cron edit "$CLOSE_JOB_ID" --session "session:market-us-live-$DATE"

LIVE_SESSION=$(HOME="$OPENCLAW_HOME" openclaw cron get "$LIVE_JOB_ID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('sessionTarget'))")
CLOSE_SESSION=$(HOME="$OPENCLAW_HOME" openclaw cron get "$CLOSE_JOB_ID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('sessionTarget'))")

test "$LIVE_SESSION" = "session:market-us-live-$DATE"
test "$CLOSE_SESSION" = "session:market-us-live-$DATE"

printf 'US session reset: %s\n' "$DATE"
```

## Rules

- Do not edit `market-us-premarket`.
- Do not delete files.
- Output only the final `US session reset: <DATE>` line.
- In constrained cron sessions, use `openclaw cron edit --session` through the CLI.
