#!/usr/bin/env python3
"""Automated cron job setup script for the NeoAlpha skill in OpenClaw.

Designed for both human operators and AI agents to register or update the 8 required cron jobs.
Supports multiple notification channels (Feishu, Discord, Telegram, Slack, etc.).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Identify workspace and openclaw paths
ROOT = Path(__file__).resolve().parents[3]
OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_STATE_DIR", Path.home() / ".openclaw"))
JOBS_FILE = OPENCLAW_DIR / "cron" / "jobs.json"

JOBS_TEMPLATE = [
    {
        "name": "market-hk-premarket",
        "schedule": {"kind": "cron", "expr": "30 8 * * 1-5", "tz": "Asia/Hong_Kong"},
        "payload": {
            "kind": "agentTurn",
            "message": "Read skills/neoalpha/cron/market-hk-premarket.md and execute it. Silent execution: final response only after strategy file validates; final response must be the briefing only, with no progress or validation-status text.",
            "timeoutSeconds": 600,
            "lightContext": True,
            "toolsAllow": ["read", "exec", "process", "write"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-us-premarket",
        "schedule": {"kind": "cron", "expr": "30 8 * * 1-5", "tz": "America/New_York"},
        "payload": {
            "kind": "agentTurn",
            "message": "Read skills/neoalpha/cron/market-us-premarket.md and execute it. Silent execution: final response only after strategy file validates; final response must be the briefing only, with no progress or validation-status text.",
            "timeoutSeconds": 600,
            "lightContext": True,
            "toolsAllow": ["read", "exec", "process", "write"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-hk-live",
        "schedule": {"kind": "cron", "expr": "*/30 9-15 * * 1-5", "tz": "Asia/Hong_Kong"},
        "payload": {
            "kind": "agentTurn",
            "message": "Run `python3 skills/neoalpha/scripts/cron_notify.py -- python3 skills/neoalpha/scripts/run_hk_live_check.py` with the exec tool immediately. Do not output visible text before the tool call. After the command finishes, reply exactly `NO_REPLY`.",
            "timeoutSeconds": 300,
            "lightContext": True,
            "toolsAllow": ["exec", "process"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-us-live",
        "schedule": {"kind": "cron", "expr": "*/30 9-15 * * 1-5", "tz": "America/New_York"},
        "payload": {
            "kind": "agentTurn",
            "message": "Run `python3 skills/neoalpha/scripts/cron_notify.py -- python3 skills/neoalpha/scripts/run_us_live_check.py` with the exec tool immediately. Do not output visible text before the tool call. After the command finishes, reply exactly `NO_REPLY`.",
            "timeoutSeconds": 300,
            "lightContext": True,
            "toolsAllow": ["exec", "process"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-hk-close",
        "schedule": {"kind": "cron", "expr": "0 16 * * 1-5", "tz": "Asia/Hong_Kong"},
        "payload": {
            "kind": "agentTurn",
            "message": "Run `python3 skills/neoalpha/scripts/cron_notify.py -- python3 skills/neoalpha/scripts/generate_hk_close_review.py` with the exec tool immediately. Do not output visible text before the tool call. After the command finishes, reply exactly `NO_REPLY`.",
            "timeoutSeconds": 300,
            "lightContext": True,
            "toolsAllow": ["exec", "process"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-us-close",
        "schedule": {"kind": "cron", "expr": "0 16 * * 1-5", "tz": "America/New_York"},
        "payload": {
            "kind": "agentTurn",
            "message": "Run `python3 skills/neoalpha/scripts/cron_notify.py -- python3 skills/neoalpha/scripts/generate_us_close_review.py` with the exec tool immediately. Do not output visible text before the tool call. After the command finishes, reply exactly `NO_REPLY`.",
            "timeoutSeconds": 300,
            "lightContext": True,
            "toolsAllow": ["exec", "process"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-hk-session-reset",
        "schedule": {"kind": "cron", "expr": "15 19 * * 1-5", "tz": "Asia/Hong_Kong"},
        "payload": {
            "kind": "agentTurn",
            "message": "Read skills/neoalpha/cron/market-hk-session-reset.md and execute it.",
            "timeoutSeconds": 600,
            "lightContext": True,
            "toolsAllow": ["read", "exec", "process", "write", "cron"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    },
    {
        "name": "market-us-session-reset",
        "schedule": {"kind": "cron", "expr": "15 19 * * 1-5", "tz": "America/New_York"},
        "payload": {
            "kind": "agentTurn",
            "message": "Read skills/neoalpha/cron/market-us-session-reset.md and execute it.",
            "timeoutSeconds": 600,
            "lightContext": True,
            "toolsAllow": ["read", "exec", "process", "write", "cron"]
        },
        "sessionTarget": "isolated",
        "agentId": "silvermoon"
    }
]

def load_existing_jobs() -> dict[str, str]:
    """Find existing NeoAlpha jobs in ~/.openclaw/cron/jobs.json and return {name: id}."""
    if not JOBS_FILE.exists():
        return {}
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            jobs = data.get("jobs", [])
            return {job["name"]: job["id"] for job in jobs if "name" in job and "id" in job}
    except Exception as e:
        print(f"Warning: Could not read {JOBS_FILE}: {e}", file=sys.stderr)
        return {}

def remove_job(job_id: str, name: str) -> bool:
    """Invoke openclaw cron rm to remove a job."""
    print(f"Removing existing job '{name}' (ID: {job_id})...")
    result = subprocess.run(["openclaw", "cron", "rm", job_id], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Failed to remove job '{name}': {result.stderr.strip()}", file=sys.stderr)
        return False
    return True

def add_job(job_def: dict) -> bool:
    """Invoke openclaw cron add to register a job."""
    name = job_def["name"]
    print(f"Adding job '{name}'...")
    json_str = json.dumps(job_def)
    result = subprocess.run(["openclaw", "cron", "add", json_str], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Failed to add job '{name}': {result.stderr.strip()}", file=sys.stderr)
        return False
    return True

def main() -> int:
    parser = argparse.ArgumentParser(description="Set up NeoAlpha cron jobs automatically.")
    parser.add_argument("--channel", default="none", help="Cron delivery channel (e.g. feishu, discord, telegram, slack, none)")
    parser.add_argument("--to", default="", help="Recipient handle or user ID for delivery (e.g. user:ou_xxx or @username)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing jobs with the same name without asking")
    args = parser.parse_args()

    # Load existing jobs
    existing_jobs = load_existing_jobs()

    success_count = 0
    for job in JOBS_TEMPLATE:
        name = job["name"]
        
        # Prepare delivery target if specified
        if args.channel and args.channel.lower() != "none":
            job["delivery"] = {
                "channel": args.channel.lower(),
                "mode": "announce"
            }
            if args.to:
                job["delivery"]["to"] = args.to

        # Handle existing jobs
        if name in existing_jobs:
            job_id = existing_jobs[name]
            if args.force:
                if not remove_job(job_id, name):
                    continue
            else:
                print(f"Job '{name}' already exists (ID: {job_id}). Use --force to overwrite. Skipping.")
                continue

        # Add the job
        if add_job(job):
            success_count += 1

    print(f"\nCron job setup complete. Registered {success_count}/{len(JOBS_TEMPLATE)} jobs.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
