#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <model.xlsx> [report.json]" >&2
  exit 2
fi

file="$1"
report="${2:-}"

if [[ ! -f "$file" ]]; then
  echo "ERROR: file not found: $file" >&2
  exit 1
fi

if ! command -v officecli >/dev/null 2>&1; then
  echo "ERROR: officecli not found in PATH" >&2
  exit 1
fi

# Set workbook calculation mode to automatic. fullCalcOnLoad is read-only in officecli v1.0.83,
# so Excel/LibreOffice may still need to open/save the workbook to refresh cached values.
officecli set "$file" / --prop calc.mode=auto --prop calc.fullPrecision=true >/tmp/financial_officecli_set.$$ 2>&1 || {
  cat /tmp/financial_officecli_set.$$ >&2
  rm -f /tmp/financial_officecli_set.$$
  exit 1
}
rm -f /tmp/financial_officecli_set.$$

validation_json=$(officecli validate "$file" --json || true)
workbook_json=$(officecli get "$file" / --json)
formula_json=$(officecli get "$file" /DCF/B18 --json 2>/dev/null || true)
formula_json2=$(officecli get "$file" /WACC/B14 --json 2>/dev/null || true)

python3 - "$file" "$report" <<'PY'
import json, subprocess, sys
from pathlib import Path
file = sys.argv[1]
report = sys.argv[2]

def run_json(args):
    try:
        proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if proc.returncode != 0:
            data["exit_code"] = proc.returncode
            if proc.stderr.strip():
                data["stderr"] = proc.stderr.strip()
        return data
    except Exception as e:
        return {"error": str(e)}

result = {
    "file": file,
    "officecli": subprocess.check_output(["officecli", "--version"], text=True).strip(),
    "workbook": run_json(["officecli", "get", file, "/", "--json"]),
    "validation": run_json(["officecli", "validate", file, "--json"]),
    "formula_spots": {
        "DCF_B18_terminal_growth": run_json(["officecli", "get", file, "/DCF/B18", "--json"]),
        "WACC_B14_wacc": run_json(["officecli", "get", file, "/WACC/B14", "--json"]),
        "Sensitivity_D6_center": run_json(["officecli", "get", file, "/Sensitivity/D6", "--json"]),
    },
    "note": "officecli sets calc.mode=auto and validates OpenXML; it does not execute formula recalculation. Open in Excel/LibreOffice to refresh cached values.",
}
text = json.dumps(result, ensure_ascii=False, indent=2)
if report:
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(text + "\n")
print(text)
PY
