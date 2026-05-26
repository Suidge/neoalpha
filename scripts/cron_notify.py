#!/usr/bin/env python3
"""Run a cron command and send non-silent stdout to Feishu bot DM.

Bundled with the NeoAlpha skill so published installs are self-contained.
The workspace-level ``scripts/cron_notify.py`` is kept for non-NeoAlpha cron
jobs; this copy is used exclusively by NeoAlpha cron payloads.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


# workspace root — same convention as every other NeoAlpha script
ROOT = Path(__file__).resolve().parents[3]


def _find_lark_cli() -> Path:
    """Resolve lark-cli binary: env override → PATH → npm-global fallback."""
    env = os.environ.get("LARK_CLI_PATH")
    if env:
        return Path(env)
    which = shutil.which("lark-cli")
    if which:
        return Path(which)
    fallback = Path.home() / ".npm-global" / "bin" / "lark-cli"
    return fallback


LARK_CLI = _find_lark_cli()


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def send_feishu(text: str, user_id: str, dry_run: bool) -> None:
    if dry_run:
        print("DRY_RUN_MESSAGE_BEGIN")
        print(text)
        print("DRY_RUN_MESSAGE_END")
        return
    if not LARK_CLI.exists():
        raise RuntimeError(f"lark-cli not found: {LARK_CLI}")

    minute = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")
    digest = hashlib.sha256(f"{minute}\n{text}".encode()).hexdigest()[:24]
    result = run(
        [
            str(LARK_CLI),
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--user-id",
            user_id,
            "--markdown",
            text,
            "--idempotency-key",
            f"cron-notify-{digest}",
        ],
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "lark send failed")


def _load_default_user_id() -> str:
    """Resolve Feishu user-id: env var → skill-local config → empty."""
    env = os.environ.get("FEISHU_NOTIFY_USER_ID", "")
    if env:
        return env
    config_path = Path(__file__).resolve().parent.parent / "notify-config.json"
    if config_path.exists():
        import json
        try:
            data = json.loads(config_path.read_text(errors="replace"))
            return data.get("feishu_user_id", "")
        except Exception:
            pass
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default=_load_default_user_id())
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.user_id:
        print("Note: Feishu user-id not set. Alerts will be output to stdout for native OpenClaw delivery.", file=sys.stderr)

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise SystemExit("missing command")

    result = run(command, timeout=args.timeout)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        if stderr:
            print(stderr, file=sys.stderr)
        if stdout:
            print(stdout, file=sys.stderr)
        return result.returncode

    if stdout and not stdout.upper().startswith("NO_REPLY"):
        if args.user_id:
            send_feishu(stdout, args.user_id, dry_run=args.dry_run)
            print("NO_REPLY")
        else:
            # Output natively so OpenClaw's native delivery channels can capture and send it
            print(stdout)
    else:
        print("NO_REPLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
