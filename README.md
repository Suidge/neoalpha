# NeoAlpha: Quantamental Investing System for OpenClaw

NeoAlpha 是一个面向多市场（美股、港股、A 股）的系统化投资研究与市场监控技能。它融合“主观基本面研究（Thesis-Driven）”与“量化数据流（Quantamental）”，将 Longbridge 行情数据、个股 Thesis 异步管理、SMAM 动量扫描、DCF 估值建模、自然语言组合 Ledger 和自动化交易日节奏（盘前/盘中/收盘）串联成一套可复盘、可验证的个人投研操作系统。

> 核心原则：本系统只做深度研究、策略监控和资产记录，不提供自动下单或盲目跟风功能。

## 为什么需要 NeoAlpha

个人投研常见的问题不是缺少信息，而是信息、判断和行动记录彼此割裂：新闻在网页里，财报数据在行情软件里，个股逻辑在聊天记录里，交易记录在另一个表格里。NeoAlpha 的目标是把这些环节串成一条工作流，让每一次研究、筛选、跟踪和复盘都能留下结构化证据。

它适合三类场景：

- 研究一家公司时，快速建立从基本面、催化剂、估值到风险的 thesis。
- 盘前和盘中需要同时看市场状态、板块轮动、动量变化和个股触发。
- 管理个人持仓时，希望用交易流水重建持仓快照，并把持仓变化和 thesis 状态挂钩。

## 核心能力

### 1. Thesis-Driven 个股研究

NeoAlpha 使用 Markdown thesis 文件沉淀公司画像、核心催化、财务与估值、技术面、风险因素、反证条件和操作框架。每个持仓或重点观察标的都有独立文件，适合长期迭代。

默认 thesis 目录放在技能仓库外：

```text
~/Documents/neoalpha/thesis-tracker
```

也可以通过环境变量覆盖：

```bash
export INVESTMENT_THESIS_DIR="/path/to/thesis-tracker"
```

命名规则：

- 美股：`<SYMBOL>.US.md`，例如 `TLN.US.md`
- 港股/A 股：`<CODE>.<MARKET>-<公司名>.md`，例如 `0700.HK-腾讯控股.md`、`300394.SZ-天孚通信.md`

文件名前缀就是 Longbridge symbol，脚本能稳定解析；公司名保留给人阅读。

### 2. Longbridge 数据优先的研究纪律

NeoAlpha 优先使用 Longbridge CLI 获取行情、K 线、基本面、公告、新闻、估值和事件数据。研究输出强调：

- 数字必须可验证，不能凭印象写结论。
- 事实和推断分开，先列证据再给判断。
- 估值、催化剂、风险和反证条件同时出现。
- 短线动量和长期 thesis 分开处理，避免把交易信号误当长期逻辑。

当 Longbridge 数据不足时，公开网页搜索只作为补充来源。

### 3. SMAM 动量扫描与 Preset 选股器 (v2 基座+亮点架构)

NeoAlpha 内置全新升级的 **v2 双层选股器评分引擎**，可从 thesis 标的、持仓池或自定义标的分组中进行大批量扫描：

- **基座风控过滤**：对趋势、动量、相对强度、流动性、题材及基本面核心因子计算加权基座分，未达合格线（短线 50 分，长线 40 分）直接风控拦截（Avoid / Reject）。
- **独立亮点触发**：引入单针洗盘、布林收缩 (TTM Squeeze)、K线形态反转、简化缠论背驰、VCP 波动收缩、相对强度 (RS vs Benchmark) 等高胜率择时亮点，独立计算，一有触发即刻标记。
- **高性能与防限流**：引入 12 小时本地文件级行情缓存层，暖缓存下大批量个股扫描从 3 分钟降至 2 秒左右，冷缓存首次运行严格保持完全串行与安全 0.2s 延时，彻底杜绝 Longbridge 行情 429 限速问题。

常用命令：

```bash
python3 skills/neoalpha/scripts/screen_momentum.py --from-thesis
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --preset short_term_momentum
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --preset long_term_compounder
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --market CN --preset short_term_momentum
python3 skills/neoalpha/scripts/screen_stocks.py --group ai_infra --preset long_term_compounder
```

选股器支持按子市场和命名分组批量扫描。`--market` 可取 `US/HK/CN/A/SH/SZ`，其中 `CN/A` 表示沪深 A 股。命名分组默认读取 `~/Documents/neoalpha/symbol-groups.json`，也可用 `--group-file` 指定；JSON 可写成：

```json
{
  "ai_infra": ["300394.SZ", "AVGO.US", "MRVL.US"],
  "cn_semis": {"symbols": ["002371.SZ", "600584.SH", "688110.SH"]}
}
```

`--group` 直接扫描分组，`--group-filter` 在 `--from-thesis`、`--symbols` 或 `--momentum-json` 的结果上取交集。

盘前策略会吸收这些筛选结果，减少只凭单条新闻或主观偏好做判断。

### 4. 自动化交易日节奏

NeoAlpha 提供盘前、盘中、收盘三段式工作流，覆盖美股、港股和 A 股观察。

- 盘前：生成市场主假设、风险状态、板块轮动、动量扫描和重点标的观察。
- 盘中：优先评估市场状态，再处理个股触发；已触发条件不会无意义重复刷屏。
- 收盘：复盘指数、持仓、观察列表、风险变化和当天触发事件。
- 跨市场：按实际开市市场过滤标的，港股休市但 A 股交易时仍可输出 A 股播报。

这套机制把“市场环境”和“个股动作”拆开处理，避免盘中被单一标的波动牵着走。

### 5. 自然语言 Portfolio Ledger

NeoAlpha 的组合记录遵循一个原则：交易流水是事实来源，持仓快照是生成产物。

```bash
python3 skills/neoalpha/scripts/portfolio_ledger.py record "<trade description>"
```

脚本会把自然语言交易描述转成结构化流水，再重建：

- `memory/strategies/portfolio/transactions.csv`：交易流水，唯一事实来源
- `memory/strategies/portfolio/positions-current.json`：当前持仓快照
- `memory/strategies/portfolio/positions-tracker.md`：人类可读持仓跟踪

如果价格、数量、方向或 symbol 不明确，应先确认再记录。

### 6. DCF 与 Excel 建模辅助

NeoAlpha 包含 DCF 模型生成和验证脚本，用于快速生成可打开、可校验的 Excel 工作簿。适合做：

- Bear / Base / Bull 三情景估值
- DCF 关键假设整理
- 公式结构校验
- Excel 自动重算参数设置

OfficeCLI 可用于 workbook finalization，最终建议用 Microsoft Excel 打开后重算并人工检查。

### 7. 发布友好的隐私隔离

NeoAlpha 的技能代码、模板、通用参考文档和脚本可以公开发布；个人 thesis、持仓、交易流水、盘中状态、策略输出和 owner prompts 不应进入公开仓库。

因此实际 thesis 默认放在：

```text
~/Documents/neoalpha/thesis-tracker
```

而不是技能目录内部。公开仓库只保留通用机制，不携带个人研究资产。

## 安装要求

- OpenClaw with skill support
- Python 3.10+
- Longbridge CLI 已安装并完成认证
- 可选：OfficeCLI，用于 Excel workbook finalization

## 安装

本技能支持极简的 AI 助手一键代劳部署以及人类手动安装。

### 自动化一键安装 (AI 推荐 🤖)

如果您正在使用 AI 编程助手（如 Claude、Gemini、Antigravity-ide 或其他 Agentic AI Coder）为您在 OpenClaw 中配置和部署本技能，请直接将以下 Prompt 复制并发送给它：

> [!TIP]
> **请将以下内容发送给您的 AI 助手：**
> 
> "请打开并完整阅读本技能目录下的 `INSTALLATION.md` 文件。该文件包含了供 AI 代理人一键自动部署的结构化指令与序列化命令。请按照 `INSTALLATION.md` 中第一步到第五步的步骤，在我的 OpenClaw 工作区中自动完成 NeoAlpha 技能的完整安装与 Cron 后台任务的自动化注册。"

---

### 手动安装指引

如果您是人类操作者，我们为您编写了非常详尽、包含多通道（飞书/Discord/Telegram/Slack）通知订阅以及故障排查的完整安装手册，请直接移步阅读：

➡️ **[INSTALLATION.md (完整安装与配置指南)](INSTALLATION.md)**

简要手动安装步骤如下：
1. 将技能目录复制到 `~/.openclaw/workspace/skills/neoalpha/`。
2. 创建 `~/.openclaw/workspace/memory/strategies/portfolio` 目录。
3. 将 `templates/` 下的两个盘前提示词模板复制到 `memory/strategies/` 下。
4. 使用 `scripts/setup_cron.py` 自动化注册或手动配置 8 个 Cron 定时任务。

## 常用入口

```bash
python3 skills/neoalpha/scripts/screen_momentum.py --from-thesis
python3 skills/neoalpha/scripts/screen_stocks.py --from-thesis --preset short_term_momentum
python3 skills/neoalpha/scripts/portfolio_ledger.py record "<trade description>"
python3 skills/neoalpha/scripts/validate_us_strategy.py
python3 skills/neoalpha/scripts/validate_hk_strategy.py
```

核心文档：

- [SKILL.md](SKILL.md)：技能入口和路由规则
- [references/market-operations.md](references/market-operations.md)：盘面分析、交易时段与 Extended Hours 防误用规则
- [references/thesis-tracker.md](references/thesis-tracker.md)：thesis 管理规则
- [references/quick-reference.md](references/quick-reference.md)：请求路由速查
- [references/momentum-model.md](references/momentum-model.md)：SMAM 动量模型
- [references/portfolio-monitoring.md](references/portfolio-monitoring.md)：组合监控
- [references/architecture.md](references/architecture.md)：系统架构

## 公开发布隐私检查

发布到 GitHub 或 ClawHub 前，不要包含：

- 个人 thesis 文件
- 组合交易流水、当前持仓、生成策略、盘中状态文件或 owner prompts
- API keys、OAuth tokens、cookie、session 数据或 credential 文件
- 邮箱、用户 ID、聊天 ID、真实本机绝对路径、个人行程和其他隐私信息

建议发布前运行：

```bash
rg -n "(/Users/[^/ ]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|api[_-]?key|token|secret|password|Bearer|Authorization|ou_[0-9a-z]+|oc_[0-9a-z]+)" .
```

每个命中都要人工确认。文档中的通用检查规则可以保留，真实私人信息不能保留。
