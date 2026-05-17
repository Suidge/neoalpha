# Excel Toolchain — 完整版文件生成链路

## 来源与边界

- 参考：`anthropics/financial-services`（Apache 2.0）。原仓库有 `xlsx-author` 技能说明和 `dcf-model/scripts/validate_dcf.py`，但未包含通用 `recalc.py` 文件；其文档引用的是托管环境里的 `/mnt/skills/public/xlsx/recalc.py`。
- 本技能本地化实现：`scripts/build_dcf_model.py` + `scripts/validate_dcf.py` + `scripts/requirements.txt`。
- 当前环境有 OfficeCLI，可设置 workbook 自动计算属性并校验 OpenXML；但 OfficeCLI 不执行公式重算。真正 cached formula values 仍需用户打开 Excel/LibreOffice，或后续安装可 headless 重算的引擎。

## 脚本

| 脚本 | 用途 |
|------|------|
| `scripts/build_dcf_model.py` | 生成公式驱动的 DCF `.xlsx`，包含 Inputs / WACC / DCF / Sensitivity / Checks |
| `scripts/validate_dcf.py` | 从原版仓库移植并适配；检查 sheet、公式错误、DCF 逻辑定位 |
| `scripts/requirements.txt` | `openpyxl>=3.1.0` |
| `scripts/finalize_xlsx_with_officecli.sh` | 设置 workbook 自动计算属性、运行 OfficeCLI OpenXML 校验、抽查关键公式单元格 |

## 安装依赖

推荐使用 venv，避免污染全局 Python：

```bash
python3 -m venv /tmp/financial_xlsx_venv
/tmp/financial_xlsx_venv/bin/pip install -r skills/investment-system/scripts/requirements.txt
```

## 生成示例模型

```bash
/tmp/financial_xlsx_venv/bin/python skills/investment-system/scripts/build_dcf_model.py \
  --output out/model.xlsx
```

输出路径会自动创建父目录。

## 使用 JSON 输入

```bash
/tmp/financial_xlsx_venv/bin/python skills/investment-system/scripts/build_dcf_model.py \
  --input inputs.json \
  --output out/INTC.US-dcf.xlsx \
  --years 5
```

最小 JSON 结构：

```json
{
  "company": "Intel Corporation",
  "ticker": "INTC.US",
  "currency": "USD",
  "units": "millions",
  "as_of": "2026-05-11",
  "source": "Longbridge verified data, 2026-05-11",
  "historical": {
    "revenue": 1000,
    "ebit_margin": 0.18,
    "tax_rate": 0.21,
    "da_pct_revenue": 0.04,
    "capex_pct_revenue": 0.05,
    "nwc_pct_revenue_change": 0.01
  },
  "market": {
    "cash": 100,
    "debt": 250,
    "minority_interest": 0,
    "preferred_equity": 0,
    "non_operating_assets": 0,
    "diluted_shares": 100,
    "current_price": 12
  },
  "wacc": {
    "risk_free_rate": 0.045,
    "beta": 1.1,
    "equity_risk_premium": 0.055,
    "size_country_premium": 0,
    "pre_tax_cost_of_debt": 0.06,
    "debt_weight": 0.2
  },
  "scenarios": {
    "Bear": {"revenue_growth": 0.06, "ebit_margin": 0.15, "terminal_growth": 0.02},
    "Base": {"revenue_growth": 0.10, "ebit_margin": 0.18, "terminal_growth": 0.03},
    "Bull": {"revenue_growth": 0.14, "ebit_margin": 0.22, "terminal_growth": 0.035}
  }
}
```

## 验证

第一层：DCF 结构与公式检查。

```bash
/tmp/financial_xlsx_venv/bin/python skills/investment-system/scripts/validate_dcf.py \
  out/model.xlsx \
  out/validation.json
```

第二层：OfficeCLI OpenXML 校验与 workbook 计算属性设置。

```bash
skills/investment-system/scripts/finalize_xlsx_with_officecli.sh \
  out/model.xlsx \
  out/officecli-report.json
```

通过标准：

- `status = PASS`
- `error_count = 0`
- `warning_count = 0` 或只有明确可接受的“需 Excel/LibreOffice 重算值”提示
- `info` 中能看到 DCF / WACC / Sensitivity sheet 和公式数量
- `officecli validate` 无 fatal 错误；若只有 OpenXML schema warning，记录到 `officecli-report.json`
- workbook `calc.mode=auto`，且 `calc.fullCalcOnLoad=true`（如 OfficeCLI/Excel 写入）

## 建模规则

- 蓝色字体 = 硬编码输入；所有蓝色输入必须有 source comment。
- 黑色字体 = 公式；预测、折现、PV、敏感性不得写死数值。
- 绿色字体保留给跨表/外部链接，当前生成器暂未使用外部链接。
- Sensitivity 使用 5×5，中心格等于 Base case。
- Checks tab 必须包含至少：terminal growth < WACC、shares > 0、sensitivity center tie、WACC > 0。


## 当前采用路线（2026-05-11）

主人已决定先采用轻量路线：不安装 LibreOffice，也不做 Microsoft Excel AppleScript 自动化。

当前交付链路：

1. `build_dcf_model.py` 用 openpyxl 生成 `.xlsx`
2. `validate_dcf.py` 检查 DCF 结构、公式与关键逻辑
3. `finalize_xlsx_with_officecli.sh` 设置 workbook 自动计算属性、运行 OfficeCLI 校验、抽查关键公式
4. 需要人工查看/刷新 cached formula values 时，用主机已有 Microsoft Excel 打开文件，Excel 会自动重算

后续如果需要全自动刷新 cached values，再评估 LibreOffice headless 或 Microsoft Excel 自动化。

## OfficeCLI 注意事项

- `officecli validate` 可能把部分 OpenXML schema warning 以 exit code 1 返回；脚本会保留 JSON 报告，不直接丢失警告内容。
- 当前测试中，OfficeCLI 可把 workbook 设置为 `calc.mode=auto`，并读到 `calc.fullCalcOnLoad=true`。
- OfficeCLI 能读取公式和 `cachedValue`，例如 `/WACC/B14`；但它不是公式计算引擎，不能替代 Excel/LibreOffice 重算。
