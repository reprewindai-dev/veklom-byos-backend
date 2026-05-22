#!/usr/bin/env python3
"""
Agent 044 — Product Hunt Launch Prep Agent
Veklom Phase 3: User Acquisition

What it does:
- Generates a complete Product Hunt launch package (tagline, description, first comment, hunter note)
- Builds a pre-launch checklist with status tracking
- Drafts hunter outreach messages to top Product Hunt hunters
- Saves all assets locally as a launch kit

Required env vars:
  OPENAI_API_KEY

Install: pip install openai
Run:     python agent_044_product_hunt.py
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai not installed. Run: pip install openai")
    sys.exit(1)

if not os.environ.get("OPENAI_API_KEY"):
    print("[ERROR] Missing OPENAI_API_KEY")
    sys.exit(1)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
OUTPUT_DIR = Path("ph_launch_kit")
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("agent_044_activity.jsonl")

VEKLOM_BRIEF = """
Product: Veklom
URL: https://veklom.com
Tagline options to improve upon: "Sovereign AI Control Plane"
What it does: Enterprise AI infrastructure platform — run LangChain workflows with
governed policy checks, SHA-256 audit trails, multi-provider LLM routing (OpenAI,
Anthropic, Gemini, Groq, Ollama), BYOK support, and private Hetzner EU deployment.
Target user: Enterprise devs, AI engineers, CTOs at companies needing compliant AI.
Key differentiators: Sovereign (no AWS/GCP), auditable (SHA-256 per call), 
Multi-provider (6+ LLM providers), Governed (GPC policy gates), Metered (per-call billing).
Pricing: Usage-based, operating reserve model. Enterprise plans available.
Stage: MVP live, seeking early adopters and enterprise pilots.
"""


def log_activity(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "044-product-hunt",
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{entry['timestamp']}] [{event_type}] {data.get('message', '')[:80]}")


def generate_launch_copy() -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Product Hunt launch expert. Generate copy that is compelling, "
                    "specific, and sounds like a real founder — not marketing fluff. "
                    "Product Hunt audiences are technical and skeptical. Be concrete."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{VEKLOM_BRIEF}\n\n"
                    "Generate a Product Hunt launch package as JSON with these exact keys:\n"
                    "- tagline (max 60 chars, no period)\n"
                    "- description (max 260 chars, compelling, specific)\n"
                    "- first_comment (300-500 words: founder story, why you built it, what's next, ask for feedback)\n"
                    "- hunter_note (100 words: personal note to the hunter about why this matters)\n"
                    "- topics (array of 5 most relevant Product Hunt topics)\n"
                    "- launch_day_tweet (280 chars max, with link placeholder [URL])\n"
                    "Return only valid JSON, no markdown."
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_hunter_outreach() -> list:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Generate personalised, genuine outreach messages to Product Hunt hunters. Be brief, respectful, and specific.",
            },
            {
                "role": "user",
                "content": (
                    f"{VEKLOM_BRIEF}\n\n"
                    "Write 3 different outreach message templates for reaching out to top Product Hunt hunters "
                    "who hunt developer tools and AI products. Each should be:\n"
                    "- Max 150 words\n"
                    "- Personalised (include [HUNTER_NAME] placeholder)\n"
                    "- Mention a specific reason why Veklom fits their hunting history\n"
                    "- Include a clear ask\n"
                    "Return as JSON array with keys: template_name, message"
                ),
            },
        ],
        max_tokens=800,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("templates", data.get("messages", []))


def generate_checklist() -> list:
    return [
        {"item": "Product Hunt account created and profile complete", "done": False},
        {"item": "Thumbnail image (240x240px) created", "done": False},
        {"item": "Gallery images (1270x952px) x5 prepared", "done": False},
        {"item": "Demo video (60-120 seconds) recorded", "done": False},
        {"item": "Hunter identified and outreach sent", "done": False},
        {"item": "Product URL (veklom.com) live and fast", "done": False},
        {"item": "Pricing page clear and accessible", "done": False},
        {"item": "Launch day set (Tuesday-Thursday for max traffic)", "done": False},
        {"item": "Email list notified 24h before launch", "done": False},
        {"item": "Slack/Discord communities notified day-of", "done": False},
        {"item": "Twitter/X thread prepared for launch day", "done": False},
        {"item": "First comment drafted and ready to post", "done": False},
        {"item": "Team standing by to respond to comments within 5 minutes", "done": False},
    ]


def save_launch_kit(copy: dict, outreach: list, checklist: list):
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Main launch document
    main_file = OUTPUT_DIR / f"ph_launch_kit_{date_str}.md"
    with open(main_file, "w") as f:
        f.write("# Veklom — Product Hunt Launch Kit\n\n")
        f.write(f"Generated: {date_str}\n\n")

        f.write("## Launch Copy\n\n")
        f.write(f"**Tagline:** {copy.get('tagline', '')}\n\n")
        f.write(f"**Description:**\n{copy.get('description', '')}\n\n")
        f.write(f"**Topics:** {', '.join(copy.get('topics', []))}\n\n")
        f.write(f"**Launch Day Tweet:**\n{copy.get('launch_day_tweet', '')}\n\n")

        f.write("## First Comment (Post immediately after launch)\n\n")
        f.write(copy.get("first_comment", "") + "\n\n")

        f.write("## Hunter Note\n\n")
        f.write(copy.get("hunter_note", "") + "\n\n")

        f.write("## Hunter Outreach Templates\n\n")
        for i, template in enumerate(outreach, 1):
            if isinstance(template, dict):
                f.write(f"### Template {i}: {template.get('template_name', f'Outreach {i}')}\n\n")
                f.write(template.get("message", str(template)) + "\n\n")

        f.write("## Pre-Launch Checklist\n\n")
        for item in checklist:
            checkbox = "- [x]" if item["done"] else "- [ ]"
            f.write(f"{checkbox} {item['item']}\n")

    log_activity("LAUNCH_KIT_SAVED", {"message": f"Launch kit saved: {main_file}", "file": str(main_file)})
    print(f"Launch kit saved: {main_file}")
    return main_file


if __name__ == "__main__":
    print(f"=== Veklom Agent 044 — Product Hunt Launch Prep === {datetime.now().isoformat()}")

    print("Generating launch copy...")
    copy = generate_launch_copy()
    print(f"Tagline: {copy.get('tagline', '')}")

    print("Generating hunter outreach templates...")
    outreach = generate_hunter_outreach()

    print("Building checklist...")
    checklist = generate_checklist()

    save_launch_kit(copy, outreach, checklist)

    print("=== Agent 044 complete ===")
