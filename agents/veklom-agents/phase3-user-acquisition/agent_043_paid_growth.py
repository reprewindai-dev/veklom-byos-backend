#!/usr/bin/env python3
"""
Agent 043 — Paid Growth Intelligence Agent
Veklom Phase 3: User Acquisition

What it does:
- Generates Google Ads keyword lists with match types and bid recommendations
- Generates Facebook/LinkedIn ad copy variations (headlines + body)
- Produces a paid growth strategy brief with budget allocation recommendations
- Saves all outputs as structured files for immediate use

Required env vars:
  OPENAI_API_KEY

Install: pip install openai
Run:     python agent_043_paid_growth.py
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
OUTPUT_DIR = Path("paid_growth_assets")
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("agent_043_activity.jsonl")

VEKLOM_BRIEF = """
Product: Veklom (https://veklom.com)
Category: Enterprise AI infrastructure / Sovereign AI platform
Target audience:
  - Primary: Enterprise CTOs, VPs of Engineering, AI Leads at 50-500 person companies
  - Secondary: Senior AI/ML engineers evaluating infrastructure
  - Industries: Finance, Healthcare, Legal, SaaS companies with compliance needs
Key pain points addressed:
  - Vendor lock-in to AWS/Azure AI services
  - Lack of audit trails for AI decisions (compliance)
  - High AI API costs with no governance
  - Can't self-host but need data residency
Key differentiators:
  - Sovereign deployment (Hetzner EU, not AWS/GCP)
  - SHA-256 immutable audit trail per LLM call
  - Multi-provider routing (OpenAI, Anthropic, Gemini, Groq, Ollama)
  - BYOK (Bring Your Own Key) per tenant
  - GPC governance layer
Pricing: Usage-based + enterprise plans
Goal: Drive enterprise demo requests and free tier signups
"""


def log_activity(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "043-paid-growth",
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{entry['timestamp']}] [{event_type}] {data.get('message', '')[:80]}")


def generate_google_ads_keywords() -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a Google Ads specialist for B2B SaaS products. Generate precise, high-intent keywords.",
            },
            {
                "role": "user",
                "content": (
                    f"{VEKLOM_BRIEF}\n\n"
                    "Generate a Google Ads keyword list as JSON with:\n"
                    "- exact_match: array of 10 exact match keywords [keyword]\n"
                    "- phrase_match: array of 10 phrase match keywords\n"
                    "- broad_match_modifier: array of 8 broad match keywords\n"
                    "- negative_keywords: array of 15 negatives to exclude irrelevant traffic\n"
                    "- recommended_bid_ranges: object with low/medium/high intent ranges in USD CPC\n"
                    "Focus on high commercial intent. Return only valid JSON."
                ),
            },
        ],
        max_tokens=900,
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_ad_copy_variations() -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a B2B copywriter specializing in enterprise tech ads. "
                    "Write copy that speaks to technical decision-makers. Be specific, not generic."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{VEKLOM_BRIEF}\n\n"
                    "Generate ad copy as JSON with:\n"
                    "- google_ads: array of 5 responsive search ad variations, each with:\n"
                    "    headlines: array of 3 headlines (max 30 chars each)\n"
                    "    descriptions: array of 2 descriptions (max 90 chars each)\n"
                    "- linkedin_ads: array of 3 LinkedIn Sponsored Content variations, each with:\n"
                    "    headline (max 70 chars)\n"
                    "    body (max 150 chars)\n"
                    "    cta: one of [Learn More, Sign Up, Request Demo, Get Started]\n"
                    "- retargeting_ad: single object with headline + body for warm audience retargeting\n"
                    "Return only valid JSON."
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.6,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_budget_strategy() -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a growth strategist for B2B SaaS startups. Be specific and data-driven.",
            },
            {
                "role": "user",
                "content": (
                    f"{VEKLOM_BRIEF}\n\n"
                    "Create a 90-day paid acquisition strategy for a startup with $2,000-5,000/month budget.\n"
                    "Include:\n"
                    "1. Channel allocation (% per channel with rationale)\n"
                    "2. Month 1: Testing phase — what to test, how to measure\n"
                    "3. Month 2: Optimization — what to cut, what to scale\n"
                    "4. Month 3: Scale — projected CAC and conversion benchmarks\n"
                    "5. Key metrics to track weekly\n"
                    "6. Landing page recommendations for paid traffic\n"
                ),
            },
        ],
        max_tokens=900,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def save_all_assets(keywords: dict, ad_copy: dict, strategy: str):
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Keywords file
    kw_file = OUTPUT_DIR / f"google_ads_keywords_{date_str}.json"
    with open(kw_file, "w") as f:
        json.dump(keywords, f, indent=2)
    print(f"Keywords saved: {kw_file}")

    # Ad copy file
    copy_file = OUTPUT_DIR / f"ad_copy_variations_{date_str}.json"
    with open(copy_file, "w") as f:
        json.dump(ad_copy, f, indent=2)
    print(f"Ad copy saved: {copy_file}")

    # Strategy report
    strategy_file = OUTPUT_DIR / f"paid_growth_strategy_{date_str}.md"
    with open(strategy_file, "w") as f:
        f.write(f"# Veklom Paid Growth Strategy — {date_str}\n\n")
        f.write(strategy)
        f.write("\n\n## Google Ads Keywords Summary\n\n")
        f.write(f"- Exact match: {len(keywords.get('exact_match', []))} keywords\n")
        f.write(f"- Phrase match: {len(keywords.get('phrase_match', []))} keywords\n")
        f.write(f"- Negatives: {len(keywords.get('negative_keywords', []))} keywords\n")
    print(f"Strategy saved: {strategy_file}")

    log_activity("ASSETS_SAVED", {
        "message": f"Saved {len(keywords.get('exact_match', []))} keywords, ad copy, strategy brief",
        "files": [str(kw_file), str(copy_file), str(strategy_file)],
    })


if __name__ == "__main__":
    print(f"=== Veklom Agent 043 — Paid Growth Intelligence === {datetime.now().isoformat()}")

    print("Generating Google Ads keywords...")
    keywords = generate_google_ads_keywords()
    print(f"Generated {len(keywords.get('exact_match', []))} exact match keywords")

    print("Generating ad copy variations...")
    ad_copy = generate_ad_copy_variations()

    print("Generating budget strategy...")
    strategy = generate_budget_strategy()

    save_all_assets(keywords, ad_copy, strategy)

    print("=== Agent 043 complete ===")
