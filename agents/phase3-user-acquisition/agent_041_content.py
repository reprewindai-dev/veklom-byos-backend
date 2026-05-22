#!/usr/bin/env python3
"""
Agent 041 — Content Publishing Agent
Veklom Phase 3: User Acquisition

What it does:
- Generates SEO-optimised blog posts about Veklom topics
- Publishes to dev.to via API
- Saves posts locally as Markdown for Hashnode/Medium manual posting
- Tracks all published content to avoid duplicates

Required env vars:
  OPENAI_API_KEY
  DEVTO_API_KEY        (get from https://dev.to/settings/extensions)

Optional:
  DEVTO_ORGANIZATION   (dev.to org name if posting under an org)

Install: pip install openai requests
Run:     python agent_041_content.py
Cron:    0 9 * * 1 python /path/to/agent_041_content.py >> /var/log/veklom_041.log 2>&1
         (every Monday at 9am)
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai not installed. Run: pip install openai")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
for var in ["OPENAI_API_KEY"]:
    if not os.environ.get(var):
        print(f"[ERROR] Missing required env var: {var}")
        sys.exit(1)

LOG_FILE = Path("agent_041_activity.jsonl")
OUTPUT_DIR = Path("generated_posts")
OUTPUT_DIR.mkdir(exist_ok=True)

DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Topics to rotate through — each generates one post
CONTENT_TOPICS = [
    {
        "title": "Why Sovereign AI Infrastructure is the Next Enterprise Moat",
        "angle": "Explain why enterprises are moving away from public cloud AI (AWS Bedrock, Azure OpenAI) toward sovereign, self-hosted infrastructure. Cover data residency, compliance, cost structure, and vendor lock-in risks. Position Veklom as the solution.",
        "tags": ["ai", "enterprise", "infrastructure", "langchain"],
    },
    {
        "title": "LangChain in Production: What Nobody Tells You About Governance",
        "angle": "Deep dive into the production challenges of running LangChain at scale: audit trails, policy enforcement, token cost runaway, multi-tenant isolation, and model provider switching. Show how Veklom's GPC layer solves these.",
        "tags": ["langchain", "python", "ai", "production"],
    },
    {
        "title": "MCP (Model Context Protocol) Explained: Building Income-Generating AI Gateways",
        "angle": "Explain what MCP is, why it matters for AI agents, and how to build a metered MCP server that charges per tool call. Include a working code example using FastMCP and Veklom's billing layer.",
        "tags": ["mcp", "ai", "agents", "python"],
    },
    {
        "title": "How to Route AI Workloads Across 6 LLM Providers Without Rewriting Your Code",
        "angle": "Technical tutorial on multi-provider LLM routing: OpenAI, Anthropic Claude, Google Gemini, Groq, Ollama. Show the abstraction layer approach, fallback logic, cost optimization, and latency tradeoffs.",
        "tags": ["ai", "openai", "tutorial", "python"],
    },
    {
        "title": "SHA-256 Audit Trails for AI: Making Every LLM Call Legally Defensible",
        "angle": "Why enterprises need cryptographic proof of AI decisions. How to implement immutable audit logs for LLM calls using SHA-256 hashing, what data to include, and how this enables compliance in regulated industries.",
        "tags": ["ai", "security", "compliance", "enterprise"],
    },
    {
        "title": "BYOK (Bring Your Own Key) AI Platforms: The Architecture That Changes Everything",
        "angle": "Deep dive into BYOK architecture for AI: why enterprises want it, how it works technically (key isolation per tenant, cost attribution, provider-agnostic routing), and why it's better than shared API key pools.",
        "tags": ["ai", "architecture", "saas", "enterprise"],
    },
]


# ── Utilities ─────────────────────────────────────────────────────────────────
def log_activity(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "041-content",
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{entry['timestamp']}] [{event_type}] {data.get('title', data.get('message', ''))[:80]}")


def already_published(topic_title: str) -> bool:
    if not LOG_FILE.exists():
        return False
    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("title") == topic_title and entry.get("event") in ["PUBLISHED_DEVTO", "SAVED_LOCAL"]:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def get_next_topic() -> dict | None:
    for topic in CONTENT_TOPICS:
        if not already_published(topic["title"]):
            return topic
    return None


# ── Content Generation ────────────────────────────────────────────────────────
def generate_blog_post(topic: dict) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior AI infrastructure engineer writing a high-quality technical blog post. "
                    "Write in a clear, direct, practical style — no fluff, no generic intros. "
                    "Use code examples where appropriate. Use markdown formatting with headers, code blocks, and bullets. "
                    "The post should be 800-1200 words. "
                    "At the end, include a natural 2-sentence mention of Veklom (https://veklom.com) "
                    "as a relevant solution, only if it genuinely fits the topic."
                ),
            },
            {
                "role": "user",
                "content": f"Write a blog post titled: '{topic['title']}'\n\nAngle/focus: {topic['angle']}",
            },
        ],
        max_tokens=1800,
        temperature=0.65,
    )
    return response.choices[0].message.content.strip()


# ── Publishing ────────────────────────────────────────────────────────────────
def publish_to_devto(topic: dict, content: str, dry_run: bool = False) -> str | None:
    if not DEVTO_API_KEY:
        print("[SKIP] No DEVTO_API_KEY set — skipping dev.to publish")
        return None

    payload = {
        "article": {
            "title": topic["title"],
            "body_markdown": content,
            "tags": topic["tags"][:4],
            "published": not dry_run,
            "canonical_url": "https://veklom.com/blog",
        }
    }

    if dry_run:
        print(f"[DRY RUN] Would publish to dev.to: {topic['title']}")
        return "dry-run"

    response = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )

    if response.status_code in (200, 201):
        data = response.json()
        url = data.get("url", "unknown")
        log_activity("PUBLISHED_DEVTO", {"title": topic["title"], "url": url, "tags": topic["tags"]})
        return url
    else:
        log_activity("ERROR", {"title": topic["title"], "message": f"dev.to API error: {response.status_code} {response.text[:200]}"})
        return None


def save_locally(topic: dict, content: str) -> Path:
    slug = topic["title"].lower().replace(" ", "-").replace(":", "").replace(",", "")[:60]
    filename = OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d')}_{slug}.md"
    with open(filename, "w") as f:
        f.write(f"# {topic['title']}\n\n")
        f.write(f"Tags: {', '.join(topic['tags'])}\n\n")
        f.write(content)
    log_activity("SAVED_LOCAL", {"title": topic["title"], "file": str(filename)})
    print(f"Saved locally: {filename}")
    return filename


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Veklom Content Publishing Agent 041")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't publish")
    parser.add_argument("--all", action="store_true", help="Generate all topics (ignores already-published check)")
    args = parser.parse_args()

    print(f"=== Veklom Agent 041 — Content Publisher === {datetime.now().isoformat()}")

    if args.all:
        topics = CONTENT_TOPICS
    else:
        topic = get_next_topic()
        topics = [topic] if topic else []

    if not topics:
        print("All topics already published. Add new topics to CONTENT_TOPICS to continue.")
        sys.exit(0)

    for topic in topics:
        print(f"\nGenerating: {topic['title']}")
        content = generate_blog_post(topic)
        save_locally(topic, content)
        url = publish_to_devto(topic, content, dry_run=args.dry_run)
        if url and url != "dry-run":
            print(f"Published: {url}")
        time.sleep(5)

    print("\n=== Agent 041 complete ===")
