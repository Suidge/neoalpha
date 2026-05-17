# Skills Gap Analysis → ZhuLinsen/daily_stock_analysis

> **评估日期**: 2026-05-16
> **对比对象**: ZhuLinsen/daily_stock_analysis (GitHub, 400+ stars) vs 我们的 financial + proactive-trader

> [!NOTE]
> **归档文档** — 本文档中的 P0(四段式输出)、P1(策略 YAML 库)、P1(Battle Plan 四点狙击) 建议已在 v3.0.0 合并中落实。剩余 P2/P3 建议可作为后续参考。合并已完成，技能名称已从 financial + proactive-trader 变更为 investment-system。

---

## 一、项目概况

ZhuLinsen 是一个完整的 LLM 驱动股票分析系统：
- 数据层：TickFlow / AkShare / Tushare / YFinance / Longbridge 多源聚合
- 分析层：`AnalysisResult` 四大板块输出结构
- 策略层：11 种内置策略 YAML（自然语言驱动，零代码）
- 模板层：Jinja2 报告模板（Markdown/微信/简报多格式）
- 推送层：企业微信/飞书/Telegram/Discord/Slack/邮件多渠道

---

## 二、对方比我们强的部分（值得吸取）

### 2.1 分析输出结构（四大板块）⭐⭐⭐⭐⭐

对方 `AnalysisResult` 有非常清晰的四段式结构：

```
dashboard:
├── core_conclusion     → 一句话结论 + 信号类型 + 仓位建议
├── data_perspective    → 趋势状态 + 价格位置 + 量能 + 筹码结构
├── intelligence        → 新闻 + 风险警报 + 积极催化剂 + 情绪 + 财报展望
└── battle_plan         → 狙击点 + 仓位策略 + 操作检查清单
```

**我们的现状**：proactive-trader 策略 JSON 只是 `monitors[{symbol, focus, triggers[]}]`——纯触发器列表，没有结论层、情报层、作战计划层。

**差距**：我们的盘前策略产出是"技术清单"而非"决策报告"。

### 2.2 策略体系（策略问股 YAML 框架）⭐⭐⭐⭐⭐

对方有 11 种内置策略，每个都是独立的 YAML 文件：
- `bull_trend.yaml`（多头趋势，默认）
- `box_oscillation.yaml`（箱体震荡）
- `volume_breakout.yaml`（放量突破）
- `shrink_pullback.yaml`（缩量回踩）
- `ma_golden_cross.yaml`（均线金叉）
- `chan_theory.yaml`（缠论）
- `emotion_cycle.yaml`（情绪周期）
- `dragon_head.yaml`（龙头战法）
- `bottom_volume.yaml`（底部放量）
- `one_yang_three_yin.yaml`（一阳三阴）

策略 YAML 结构清晰：
```yaml
name / display_name / description / category / core_rules / required_tools / instructions
```

**我们的现状**：策略逻辑散落在 cron .md 指令文件中（市场方向判断、触发条件），没有结构化策略库。

**差距**：我们的策略是"硬编码在流程中的"，不是"可插拔配置的"。

### 2.3 操作清单（Battle Plan + Sniper Points）⭐⭐⭐⭐

对方的 `battle_plan` 包含：
- Sniper Points：理想买点 / 次选买点 / 止损位 / 止盈位（四点一线）
- Position Strategy：建议仓位 + 进场计划 + 风控
- Action Checklist：可执行操作清单

**我们的现状**：thesis 文件有关键价位表，但没有"四点狙击"格式。操作框架有建仓/加仓/止损，但没有整合成 checklist。

### 2.4 大盘复盘（Market Review）⭐⭐⭐

对方有独立的 `perform_market_review()` 功能，输出综合市场复盘报告。

**我们的现状**：proactive-trader 的 close review 是"逐标的触发回顾"，不是全局市场复盘。

### 2.5 多格式报告模板 ⭐⭐

对方有 Jinja2 模板：`report_markdown.j2`（6697B 完整报告）、`report_wechat.j2`（微信适配）、`report_brief.j2`（简报）。

**我们的现状**：策略文件是 Markdown 混 JSON，没有模板引擎。

---

## 三、我们比对方强的部分

| 能力 | 我们 | 对方 |
|------|------|------|
| **Thesis 跟踪系统** | ✅ thesis-tracker + Step 0-8 增强框架 | ❌ 无长期 thesis 管理 |
| **SMAM 动量模型** | ✅ 学术级 CMS/Stability/VAM/VM_Score | ❌ 无明确定义动量模型 |
| **数据源覆盖** | ✅ Longbridge 覆盖 US/HK/CN，实时 + 历史 | ✅ 多源但依赖爬虫稳定性 |
| **Cron 自动化** | ✅ premarket/live/close 三阶段全自动 | ✅ GitHub Actions 定时 |
| **持仓跟踪** | ✅ positions-tracker 补充 Longbridge | ✅ 内置持仓管理 |
| **估值工具链** | ✅ DCF xlsx 生成 + 验证 | ❌ 无建模能力 |

---

## 四、优化建议（不照搬，只吸取）

### 建议 1：升级盘前策略输出为四段式 🏆 最高优先级

**做什么**：将 `us-daily.md` / `hk-daily.md` 的格式从"Top Call + Monitors"改为四段式：

```
# {日期} {市场}盘前策略

## 📌 核心结论（Core Conclusion）
[一句话定调 + 信号类型(积极/中性/谨慎) + 仓位建议]

## 📊 数据视角（Data Perspective）
[大盘趋势 / 关键价格位置 / 量能判断 / 资金面]

## 📰 情报汇总（Intelligence）
[关键新闻 / 风险警报 / 积极催化 / SMAM 动量概览]

## 🎯 作战计划（Battle Plan）
[重点标的 + 狙击点 + 仓位建议 + 操作清单]
```

**不改动**：proactive-trader-strategy JSON block 保留（live 校验需要），但人类可读部分升级。

### 建议 2：创建策略 YAML 库 🏆 高优先级

**做什么**：在 proactive-trader 下新建 `strategies/` 目录，存放自然语言策略 YAML：

```yaml
# skills/proactive-trader/strategies/momentum_add.yaml
name: momentum_add
display_name: 动量加仓策略
description: SMAM Q1/Q2 + 回调至支撑位 → 加仓
instructions: |
  1. SMAM CMS > +0.25（正动量）
  2. 价格回调至 MA20 或关键支撑位附近
  3. 检查逻辑破坏条件是否触发
  4. 输出：狙击买点 / 仓位 / 止损
```

**为什么这样做**：盘前 cron 的模型研判可以引用策略 YAML 作为"操作手册"，而不是每次都靠 prompt 指令重述。

### 建议 3：Thesis 文件增加 Battle Plan 模板 🏆 高优先级

**做什么**：在 thesis 模板中增加标准化的四点狙击格式：

```
## 🎯 作战计划（Battle Plan）

| 类型 | 价格 | 条件 |
|------|------|------|
| 🎯 理想买点 | ¥58 | 回调至 2-3 月平台 + SMAM CMS>0 |
| 🔵 次选买点 | ¥63 | 4 月低点附近 + SMAM CMS>0 |
| 🛑 止损 | ¥47 | 跌破 3 月最低 OR 逻辑破坏触发 |
| 🎊 止盈 | ¥90 / ¥120 | 中期目标 / 长期目标 |
```

### 建议 4：增强 Close Review → 大盘复盘 🏆 中优先级

**做什么**：在 `proactive_trader.py` 的 `close_review()` 中增加全局市场复盘段落（指数表现、板块轮动、资金流向、情绪温度），不只输出逐标的触发回顾。

### 建议 5：多格式策略输出（可选）⭐ 低优先级

目前不做 Jinja2 模板化（增加复杂度且我们的 Markdown 输出已经够用），但保留未来可能性。

---

## 五、不做的事

| 不做什么 | 原因 |
|---------|------|
| 照搬对方代码库 | 我们有 OpenClaw + Longbridge 自有架构 |
| 多源数据爬虫 | Longbridge 已经更稳定、更全面 |
| Web UI | 我们是 Discord 交互 + cron，不需要 Web |
| 多渠道推送模板 | OpenClaw 消息系统已处理 |
| 策略回测 | 当前聚焦决策支持，非量化回测 |

---

## 六、关于 financial + proactive-trader 合并

### 评估结论：**应该合并，但现在不适合执行**

**应该合并的理由**：
1. 两个技能高度交织（thesis 文件在 proactive-trader，分析框架在 financial）
2. SMAM 在 financial 但被 proactive-trader cron 消费
3. Step 0-8 框架在 financial 但产物 thesis 在 proactive-trader
4. 分工是历史产物，不是逻辑边界
5. 合并后触发词更简单（一个"投资分析系统"）

**现在不适合执行的理由**：
1. 盘前/盘中/盘后 cron jobs 依赖当前文件路径
2. 数据包脚本（market_us_pack.py / market_hk_pack.py）依赖 proactive-trader 路径
3. 合并需要同时迁移 15+ 个 cron job 的引用
4. 今晚的 SMAM 集成刚生效，合并引入的变动风险不值得
5. 两个技能都在正常运行，没有阻塞性问题

**建议路径**：
- 今天：创建 `SKILL.md` 级别的交叉引用，让两个技能互相指向对方
- 下次维护窗口（cron 暂停时）：执行合并
- 合并后新技能命名：`investment-system` 或 `quant-system`
- 保持向后兼容的符号链接过渡期

---

## 七、立即执行清单

| # | 行动 | 涉及文件 | 优先级 |
|---|------|---------|--------|
| 1 | ⬜ 升级盘前策略模板为四段式 | cron/market-*-premarket.md | 🏆 P0 |
| 2 | ⬜ 创建策略 YAML 库（3-5 个核心策略） | strategies/*.yaml | 🏆 P1 |
| 3 | ⬜ Thesis 模板增加 Battle Plan 四点狙击 | templates/thesis-template.md | 🏆 P1 |
| 4 | ⬜ Close review 增加大盘复盘段 | proactive_trader.py close_review() | 🏆 P2 |
| 5 | ⬜ 两技能间增加交叉引用 | financial/SKILL.md, proactive-trader/SKILL.md | P2 |
| 6 | ⬜ 计划合并窗口（需 cron 暂停） | — | P3 |
