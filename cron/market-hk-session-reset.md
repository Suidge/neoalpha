# Market HK Session Reset — 港股持久 session 轮换

香港时间 19:15（港股工作日）执行。

## 执行流程（严格按顺序）

### Step 1: 确定下一个港股交易日日期

```bash
python3 -c "
from datetime import date, timedelta
d = date.today()
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
HOME=/Users/neoshi openclaw cron edit 23b6edcc-daac-4e27-8e60-502274cc70b3 --session session:market-hk-live-<DATE>
HOME=/Users/neoshi openclaw cron edit f9fc4604-6dc2-4629-b373-a531f13f2eb7 --session session:market-hk-live-<DATE>
```

两个 job 的 `--session` 值必须相同。

### Step 3: 验证更新

```bash
HOME=/Users/neoshi openclaw cron get 23b6edcc-daac-4e27-8e60-502274cc70b3 2>/dev/null | python3 -c "import sys,json; j=json.load(sys.stdin); print(f\"live: sessionTarget={j.get('sessionTarget')}\")"
HOME=/Users/neoshi openclaw cron get f9fc4604-6dc2-4629-b373-a531f13f2eb7 2>/dev/null | python3 -c "import sys,json; j=json.load(sys.stdin); print(f\"close: sessionTarget={j.get('sessionTarget')}\")"
```

两个输出都应该是 `session:market-hk-live-<DATE>`。

### Step 4: 输出结果

```
HK session reset: 今日 → <DATE>
```

## 规则
- 不碰 market-hk-premarket cron（id: 76bb1fd3-e88f-469a-8c18-c11195366040）
- 不删除任何文件
- 只输出 Step 4 那一行
- 不要使用 cron 工具（隔离模式下受限），全部走 `HOME=/Users/neoshi openclaw cron edit --session` CLI
