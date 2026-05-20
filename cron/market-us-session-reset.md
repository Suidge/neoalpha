# Market US Session Reset — 美股持久 session 轮换

美东时间 19:15（美国工作日）执行。

## 执行流程（严格按顺序）

### Step 1: 确定下一个美股交易日日期

```bash
TZ='America/New_York' python3 -c "
from datetime import datetime, timedelta
d = datetime.now().date()
while True:
    d = d + timedelta(days=1)
    if d.weekday() < 5:
        print(d.isoformat())
        break
"
```

记下输出（格式 `2026-05-26`），后续用 `<DATE>` 代指。

### Step 2: 更新两个 cron job

**隔离 cron 模式下 cron 工具受限**，必须使用 `openclaw cron edit` CLI 配合 `--session` 参数（不是 `--session-key`）。

依次执行：

```bash
HOME=/Users/neoshi openclaw cron edit c8c3761e-2944-43c1-879e-9ce6f3b18821 --session session:market-us-live-<DATE>
HOME=/Users/neoshi openclaw cron edit 69605dab-674b-4853-9588-1962cdcdcf96 --session session:market-us-live-<DATE>
```

两个 job 的 `--session` 值必须相同。

### Step 3: 验证更新

```bash
HOME=/Users/neoshi openclaw cron get c8c3761e-2944-43c1-879e-9ce6f3b18821 2>/dev/null | python3 -c "import sys,json; j=json.load(sys.stdin); print(f\"live: sessionTarget={j.get('sessionTarget')}\")"
HOME=/Users/neoshi openclaw cron get 69605dab-674b-4853-9588-1962cdcdcf96 2>/dev/null | python3 -c "import sys,json; j=json.load(sys.stdin); print(f\"close: sessionTarget={j.get('sessionTarget')}\")"
```

两个输出都应该是 `session:market-us-live-<DATE>`。

### Step 4: 输出结果

```
US session reset: 今日 → <DATE>
```

## 规则
- 不碰 market-us-premarket cron（id: 10a4abd1-98fb-4e71-b845-abb574afef01）
- 不删除任何文件
- 只输出 Step 4 那一行
- 不要使用 cron 工具（隔离模式下受限），全部走 `HOME=/Users/neoshi openclaw cron edit --session` CLI
