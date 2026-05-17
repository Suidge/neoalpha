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

调用 cron 工具的 `update` action，对以下两个 job 各调用一次：

**Job 1: market-us-live**
```
cron update jobId=c8c3761e-2944-43c1-879e-9ce6f3b18821
patch={"sessionTarget": "session:market-us-live-<DATE>"}
```

**Job 2: market-us-close**
```
cron update jobId=69605dab-674b-4853-9588-1962cdcdcf96
patch={"sessionTarget": "session:market-us-live-<DATE>"}
```

两个 job 的 sessionTarget 必须相同。

### Step 3: 确认输出

```
US session reset: 今日 → <DATE>
```

## 规则
- 不碰 market-us-premarket cron（id: 10a4abd1-98fb-4e71-b845-abb574afef01）
- 不删除任何文件
- 只输出 Step 3 那一行
