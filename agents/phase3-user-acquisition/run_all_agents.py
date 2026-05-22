#!/usr/bin/env python3
"""
Veklom Phase 3 — Agent Scheduler / Runner

Runs all Phase 3 user acquisition agents on their appropriate schedules.
Designed to be run as a single always-on process via Coolify or cron.

Schedule:
  - Agent 040 (SEO):          Every Monday 8am UTC
  - Agent 041 (Content):      Every Monday 9am UTC  
  - Agent 042 (Community):    Every 6 hours (4x daily)
  - Agent 043 (Paid Growth):  Every 2 weeks Monday 10am UTC
  - Agent 044 (Product Hunt): Once (run manually when ready to launch)

Usage:
  python run_all_agents.py              # Run scheduler (continuous)
  python run_all_agents.py --now 042    # Run agent 042 immediately
  python run_all_agents.py --dry-run    # Dry run all agents once
  python run_all_agents.py --status     # Show last run times

Required env vars: See individual agent files.
Install: pip install schedule openai praw requests
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

STATUS_FILE = Path("agent_scheduler_status.json")
AGENT_DIR = Path(__file__).parent

AGENTS = {
    "040": {
        "name": "SEO Intelligence",
        "script": "agent_040_seo.py",
        "schedule": "weekly_monday_0800",
        "description": "Audits SEO, generates keyword recommendations",
    },
    "041": {
        "name": "Content Publisher",
        "script": "agent_041_content.py",
        "schedule": "weekly_monday_0900",
        "description": "Generates and publishes blog posts to dev.to",
    },
    "042": {
        "name": "Community Outreach",
        "script": "agent_042_community.py",
        "schedule": "every_6h",
        "description": "Scans Reddit and posts genuine replies",
    },
    "043": {
        "name": "Paid Growth Intelligence",
        "script": "agent_043_paid_growth.py",
        "schedule": "biweekly_monday_1000",
        "description": "Generates ad copy, keywords, growth strategy",
    },
    "044": {
        "name": "Product Hunt Launch",
        "script": "agent_044_product_hunt.py",
        "schedule": "manual",
        "description": "Generates complete PH launch kit (run once)",
    },
}


def load_status() -> dict:
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {}


def save_status(status: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def run_agent(agent_id: str, dry_run: bool = False) -> bool:
    agent = AGENTS.get(agent_id)
    if not agent:
        print(f"[ERROR] Unknown agent: {agent_id}")
        return False

    script = AGENT_DIR / agent["script"]
    if not script.exists():
        print(f"[ERROR] Script not found: {script}")
        return False

    cmd = [sys.executable, str(script)]
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'='*60}")
    print(f"Running Agent {agent_id} — {agent['name']}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=str(AGENT_DIR))
    success = result.returncode == 0

    status = load_status()
    status[agent_id] = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "name": agent["name"],
    }
    save_status(status)

    return success


def show_status():
    status = load_status()
    print(f"\n{'='*60}")
    print("Veklom Phase 3 Agent Status")
    print(f"{'='*60}")
    for agent_id, agent in AGENTS.items():
        agent_status = status.get(agent_id, {})
        last_run = agent_status.get("last_run", "Never")
        success = agent_status.get("success", None)
        status_str = "✅" if success else ("❌" if success is False else "⏳")
        print(f"{status_str} Agent {agent_id} — {agent['name']}")
        print(f"   Schedule: {agent['schedule']}")
        print(f"   Last run: {last_run}")
        print(f"   {agent['description']}")
        print()


def run_scheduler():
    try:
        import schedule
        import time
    except ImportError:
        print("[ERROR] schedule not installed. Run: pip install schedule")
        sys.exit(1)

    print("Starting Veklom Phase 3 Agent Scheduler...")
    print("Press Ctrl+C to stop.\n")

    schedule.every().monday.at("08:00").do(run_agent, "040")
    schedule.every().monday.at("09:00").do(run_agent, "041")
    schedule.every(6).hours.do(run_agent, "042")
    schedule.every(14).days.at("10:00").do(run_agent, "043")

    # Run community agent immediately on first start
    print("Running community agent 042 on startup...")
    run_agent("042")

    print("\nScheduler running. Next runs:")
    for job in schedule.jobs:
        print(f"  {job}")

    while True:
        schedule.run_pending()
        import time
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Veklom Phase 3 Agent Scheduler")
    parser.add_argument("--now", metavar="AGENT_ID", help="Run specific agent immediately (e.g. 042)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode for all agents")
    parser.add_argument("--status", action="store_true", help="Show agent status and exit")
    parser.add_argument("--all-now", action="store_true", help="Run all agents immediately")
    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    if args.now:
        success = run_agent(args.now, dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    if args.all_now:
        for agent_id in ["040", "041", "042", "043", "044"]:
            run_agent(agent_id, dry_run=args.dry_run)
        sys.exit(0)

    run_scheduler()
