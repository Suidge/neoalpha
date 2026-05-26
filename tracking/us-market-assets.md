# US Market Asset Tracking List

美股各大类资产固定追踪清单。

---

## 🎯 触发词约定

当用户要求拉取美股大类资产走势时，直接读取本文件，按当前时间选择对应场景的命令执行：
- 盘前时段（~20:30 前）→ 用「盘前全量巡检」
- 盘中时段 → 用「盘中轻量巡检」
- 非交易时段 → 用最新收盘价 + 盘前/盘后数据

---

## 快速命令（按场景）

### 盘前全量巡检（20:30 CST）
```bash
longbridge quote INTC.US NVDA.US GOOG.US AAPL.US TSLA.US AMD.US META.US QCOM.US GLD.US SLV.US USO.US TLT.US IEF.US SHY.US UUP.US EEM.US FXI.US IBIT.US SPY.US QQQ.US DIA.US IWM.US
longbridge quote .SPX.US .IXIC.US .DJI.US .VIX.US
```
一条拿个股+ETF，一条拿指数+VIX，共 2 条命令覆盖全资产。

### 盘中轻量巡检
盘中巡检的标的和触发位由当日策略 `memory/strategies/us-daily.md` 动态决定，不在此固定。

---

## 资产对照表

### 全量标的（22个+4指数）
| 分组 | Symbols |
|------|---------|
| 大盘指数 | `.SPX.US .IXIC.US .DJI.US .VIX.US` |
| 核心个股 | `INTC.US NVDA.US GOOG.US AAPL.US TSLA.US AMD.US META.US QCOM.US` |
| 固收 | `TLT.US IEF.US SHY.US` |
| 美元 | `UUP.US` |
| 大宗 | `GLD.US SLV.US USO.US` |
| 新兴市场 | `EEM.US FXI.US` |
| 加密 | `IBIT.US` |
| 对标ETF | `SPY.US QQQ.US DIA.US IWM.US` |

### 盘中追加标的（事件驱动）
| Symbol | 名称 | 与持仓关系 |
|--------|------|-----------|
| `QCOM.US` | Qualcomm | 半导体同业/供应链 |
| `GLW.US` | Corning | 玻璃/光学材料供应商 |
| `MP.US` | MP Materials | 稀土材料供应商 |
