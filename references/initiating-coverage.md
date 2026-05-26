# Initiating Coverage — 首次覆盖任务闸门

> 来源参考：Anthropic `financial-services` initiating-coverage。这里不照搬机构长报告，而是抽取“分阶段、可验证、不可跳步”的研究闸门。

## 触发

"首次覆盖"、"initiate coverage"、"新建 thesis"、"深度研究 [公司]"、"建立覆盖"、"重仓前研究"

## 核心原则

首次覆盖必须分任务推进。不要一次性承诺完整结论；每个阶段都有明确产物和验证标准。

## 五阶段流程

### Task 1: Company Research

目标：确定公司到底是什么、靠什么赚钱、核心矛盾是什么。

产物：
- 公司简介和业务分部。
- 收入/利润/现金流历史摘要。
- 产业链位置和客户/供应商关系。
- 核心矛盾：`X vs Y`。
- 关键来源清单。

通过标准：
- 主要业务和营收占比已验证。
- 最近一期财报、年报或公告已读取。
- 不再依赖二手摘要作为主要事实来源。

### Task 2: Industry & Competitive Work

目标：判断公司所处行业是否值得研究，以及它是否有位置。

调用：
- [sector-overview.md](sector-overview.md)
- [competitive-landscape.md](competitive-landscape.md)
- [comps-analysis.md](comps-analysis.md)

产物：
- 行业规模、增长、利润池。
- 5-15 个 peer set。
- moat assessment。
- 公司相对同行的强弱项。

通过标准：
- peer set 合理，且说明为什么包括/排除。
- 至少 3 个行业关键指标已验证。
- 竞争格局能支持或反驳初始 thesis。

### Task 3: Financial Model / Valuation

目标：给出 Bear/Base/Bull 的估值和核心假设。

调用：
- [dcf-model.md](dcf-model.md)
- [comps-analysis.md](comps-analysis.md)
- [model-audit.md](model-audit.md)

产物：
- 三情景估值。
- 关键假设表。
- 敏感性表。
- 估值桥接和每股价值。

通过标准：
- 每个关键输入有来源或标记 `[ASSUMPTION]`。
- Base case 中心格与敏感性表一致。
- model audit 无 Critical。

### Task 4: Thesis Construction

目标：把事实、估值、催化剂、风险写入 thesis 文件。

调用：
- [thesis-framework-enhanced.md](thesis-framework-enhanced.md)
- [thesis-tracker.md](thesis-tracker.md)
- `templates/thesis-template.md`

产物：
- 论点陈述。
- 趋势三要素。
- 质量评分。
- 逻辑破坏条件。
- Battle Plan。
- Catalyst Calendar。

通过标准：
- 至少 3 条可量化或可观测的反证条件。
- Bull/Base/Bear 与估值模型一致。
- 所有交易相关内容标注“不构成投资建议或交易指令”。

### Task 5: Final Review

目标：决定进入持仓、watchlist、继续研究或放弃。

产物：

```markdown
## 首次覆盖结论 — [公司]

结论: Long / Watch / Avoid / Short-risk
信心度: High / Medium / Low
核心理由:
1.
2.
3.

主要反证:
1.
2.
3.

下一步:
- 建立 thesis / 加入 watchlist / 跟踪催化剂 / 放弃
```

通过标准：
- 事实、推断、假设分开。
- 没有未验证数字进入核心结论。
- 下一步动作明确。

## 任务闸门

| 当前阶段 | 进入下一阶段前必须满足 |
|----------|------------------------|
| Task 1 → 2 | 公司业务和财务基础事实已验证 |
| Task 2 → 3 | peer set 和行业关键指标已确认 |
| Task 3 → 4 | 估值模型无 Critical，情景假设清楚 |
| Task 4 → 5 | thesis 可被反证，催化剂和止损信号明确 |

## 文件组织

- 研究过程笔记：必要时写入 `memory/projects/` 或临时工作文档。
- 长期跟踪结果：写入 `${INVESTMENT_THESIS_DIR:-~/Documents/neoalpha/thesis-tracker}`；美股文件名为 `<SYMBOL>.US.md`，港股/A股文件名为 `<CODE>.<MARKET>-<股票名称>.md`。
- 模型文件：如生成 xlsx，文件名包含 symbol、日期、模型类型。

## 禁止事项

- 不跳过 Task 1 直接给目标价。
- 不用旧训练数据代替最新财报。
- 不把未验证传闻写入 thesis 核心结论。
- 不把模型输出当作确定收益承诺。
