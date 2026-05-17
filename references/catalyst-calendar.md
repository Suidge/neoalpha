# Catalyst Calendar — 催化剂日历

## 触发

"催化剂"、"catalyst"、"upcoming events"、"[公司] upcoming"

## 催化剂类型

| 类型 | 数据源 |
|------|--------|
| 财报日期 | Longbridge news/filing 优先；web_search 补充 |
| 产品发布 | web_search 搜索 `[Company] product launch 2026` |
| 监管决策 | FDA、FTC、反垄断等官方来源 + web_search |
| 投资者日 | 公司 IR 页面 |
| 行业会议 | 展会、峰会 |

## 输出格式

```
📅 [公司/组合] 催化剂日历

| 日期 | 事件 | 类型 | 预期影响 |
|------|------|------|---------|
| | | | |
```

## 维护规则

- 每个 thesis 文件包含催化剂日历子表
- 事件发生后标记 ✅ 或 ❌（是否符合预期）
- 每月 review 一次，清除已过期事件
- 涉及交易机会时，末尾加入“仅供研究分析，不构成投资建议或交易指令”。
