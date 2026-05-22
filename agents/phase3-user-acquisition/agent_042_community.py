#!/usr/bin/env python3
"""
Agent 042 — Community Outreach Agent
Veklom Phase 3: User Acquisition

What it does:
- Scans Reddit hot posts in target subreddits for relevant threads
- Posts genuine, helpful replies that naturally reference Veklom
- Posts a weekly Show HN style update to r/SideProject
- Logs all activity with timestamps

Required env vars:
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USERNAME
  REDDIT_PASSWORD
  OPENAI_API_KEY

Install: pip install praw openai
Run:     python agent_042_community.py
Cron:    0 */6 * * * python /path/to/agent_042_community.py >> /var/log/veklom_042.log 2>&1
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    import praw
except ImportError:
    print("[ERROR] praw not installed. Run: pip install praw")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai not installed. Run: pip install openai")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
REQUIRED_ENV = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
    "OPENAI_API_KEY",
]

for var in REQUIRED_ENV:
    if not os.environ.get(var):
        print(f"[ERROR] Missing required env var: {var}")
        sys.exit(1)

LOG_FILE = Path("agent_042_activity.jsonl")

TARGET_SUBREDDITS = [
    "MachineLearning",
    "SideProject",
    "aiagents",
    "LangChain",
    "selfhosted",
    "LocalLLaMA",
    "artificial",
    "OpenAI",
]

KEYWORDS = [
    "sovereign ai",
    "langchain governance",
    "self-hosted llm",
    "ai audit",
    "mcp server",
    "agent infrastructure",
    "enterprise ai",
    "ai control plane",
    "llm routing",
    "bring your own key",
    "byok",
    "ai governance",
    "private llm",
    "on-premise ai",
]

VEKLOM_CONTEXT = """
Veklom is a sovereign AI control plane and marketplace. It enables enterprises
to run LangChain-based AI workflows with:
- Full governance via GPC (Governed Policy Checks)
- SHA-256 immutable audit trails per transaction
- Multi-provider LLM routing (OpenAI, Anthropic, Gemini, Groq, Ollama)
- Private Hetzner EU sovereign deployment — no AWS/GCP tax
- BYOK (Bring Your Own Key) support
- Per-tenant operating reserve billing
- MCP (Model Context Protocol) server compatibility

Website: https://veklom.com
Target users: Enterprise teams needing compliant, auditable, sovereign AI infrastructure.
"""

# ── Clients ────────────────────────────────────────────────────────────────────
reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent="VeklomCommunityBot/1.0 (sovereign AI infrastructure)",
)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── Utilities ─────────────────────────────────────────────────────────────────
def log_activity(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "042-community",
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{entry['timestamp']}] [{event_type}] {data.get('title', data.get('message', '')[:80])}")


def already_replied(post_id: str) -> bool:
    """Check if we already replied to this post in a previous run."""
    if not LOG_FILE.exists():
        return False
    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("post_id") == post_id and entry.get("event") == "REPLIED":
                    return True
            except json.JSONDecodeError:
                continue
    return False


def post_is_relevant(title: str, body: str) -> bool:
    combined = (title + " " + body).lower()
    return any(kw in combined for kw in KEYWORDS)


def generate_reply(thread_title: str, thread_body: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable AI infrastructure engineer. "
                    "You give genuinely helpful, specific, technically accurate replies on Reddit. "
                    "You never sound like a bot or salesperson. "
                    "Only mention Veklom if it is directly and naturally relevant to solving the person's problem. "
                    "If you mention Veklom, do it once, briefly, at the end. "
                    f"Context about Veklom if needed: {VEKLOM_CONTEXT}"
                ),
            },
            {
                "role": "user",
                "content": f"Reddit thread title: {thread_title}\n\nThread body:\n{thread_body[:800]}\n\nWrite a helpful reply (max 200 words).",
            },
        ],
        max_tokens=280,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_weekly_post() -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a genuine, honest Show HN / SideProject post for Reddit. "
                    "Sound like a real founder sharing progress, not marketing copy. "
                    "Include what you built, why, what stage you're at, and invite real feedback. "
                    "Max 250 words."
                ),
            },
            {
                "role": "user",
                "content": VEKLOM_CONTEXT,
            },
        ],
        max_tokens=320,
        temperature=0.8,
    )
    body = response.choices[0].message.content.strip()
    return {
        "title": "I built a sovereign AI control plane for governed LangChain workflows — Veklom (feedback welcome)",
        "body": body,
    }


# ── Main Actions ──────────────────────────────────────────────────────────────
def scan_and_reply(dry_run: bool = False) -> int:
    """Scan hot posts across target subreddits and reply to relevant ones."""
    replied_count = 0

    for sub_name in TARGET_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=15):
                if post.is_self and post_is_relevant(post.title, post.selftext):
                    if already_replied(post.id):
                        continue

                    reply_text = generate_reply(post.title, post.selftext)

                    if dry_run:
                        print(f"[DRY RUN] Would reply to r/{sub_name}: {post.title[:60]}")
                        print(f"  Reply preview: {reply_text[:120]}...")
                    else:
                        post.reply(reply_text)
                        log_activity("REPLIED", {
                            "subreddit": sub_name,
                            "post_id": post.id,
                            "title": post.title[:100],
                            "reply_preview": reply_text[:100],
                        })
                        replied_count += 1
                        time.sleep(10)  # Rate limit: Reddit allows ~1 reply per 10s

        except Exception as e:
            log_activity("ERROR", {"subreddit": sub_name, "message": str(e)})

    return replied_count


def post_weekly_update(subreddit_name: str = "SideProject", dry_run: bool = False):
    """Post the weekly Veklom progress update."""
    post_data = generate_weekly_post()

    if dry_run:
        print(f"[DRY RUN] Would post to r/{subreddit_name}:")
        print(f"  Title: {post_data['title']}")
        print(f"  Body: {post_data['body'][:200]}...")
        return

    subreddit = reddit.subreddit(subreddit_name)
    submission = subreddit.submit(
        title=post_data["title"],
        selftext=post_data["body"],
    )
    log_activity("WEEKLY_POST", {
        "subreddit": subreddit_name,
        "post_id": submission.id,
        "title": post_data["title"],
        "url": f"https://reddit.com{submission.permalink}",
    })
    print(f"Posted to r/{subreddit_name}: https://reddit.com{submission.permalink}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Veklom Community Outreach Agent 042")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without posting")
    parser.add_argument("--weekly-post", action="store_true", help="Also post the weekly SideProject update")
    parser.add_argument("--post-only", action="store_true", help="Only post weekly update, skip replies")
    args = parser.parse_args()

    print(f"=== Veklom Agent 042 — Community Outreach === {datetime.now().isoformat()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    if not args.post_only:
        count = scan_and_reply(dry_run=args.dry_run)
        print(f"Replied to {count} threads")

    if args.weekly_post or args.post_only:
        post_weekly_update(dry_run=args.dry_run)

    print("=== Agent 042 complete ===")
