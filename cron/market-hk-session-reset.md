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

调用 cron 工具的 `update` action，对以下两个 job 各调用一次：

**Job 1: market-hk-live**
```
cron update jobId=23b6edcc-daac-4e27-8e60-502274cc70b3
patch={"sessionTarget": "session:market-hk-live-<DATE>"}
```

**Job 2: market-hk-close**
```
cron update jobId=f9fc4604-6dc2-4629-b373-a531f13f2eb7
patch={"sessionTarget": "session:market-hk-live-<DATE>"}
```

两个 job 的 sessionTarget 必须相同。

### Step 3: 确认输出

```
HK session reset: 今日 → <DATE>
```

## 规则
- 不碰 market-hk-premarket cron（id: 76bb1fd3-e88f-469a-8c18-c11195366040）
- 不删除任何文件
- 只输出 Step 3 那一行
