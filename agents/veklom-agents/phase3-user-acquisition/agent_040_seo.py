#!/usr/bin/env python3
"""
Agent 040 — SEO Intelligence Agent
Veklom Phase 3: User Acquisition

What it does:
- Fetches current top-ranking keywords for sovereign AI / LangChain topics
- Generates SEO-optimised meta titles, descriptions, and H1s for Veklom pages
- Audits veklom.com pages for basic SEO signals via HTTP
- Outputs a weekly SEO recommendations report as Markdown

Required env vars:
  OPENAI_API_KEY

Install: pip install openai requests
Run:     python agent_040_seo.py
Cron:    0 8 * * 1 python /path/to/agent_040_seo.py >> /var/log/veklom_040.log 2>&1
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

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
if not os.environ.get("OPENAI_API_KEY"):
    print("[ERROR] Missing OPENAI_API_KEY")
    sys.exit(1)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
REPORT_DIR = Path("seo_reports")
REPORT_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("agent_040_activity.jsonl")

VEKLOM_PAGES = [
    {"url": "https://veklom.com", "page": "Homepage"},
    {"url": "https://veklom.com/marketplace", "page": "Marketplace"},
    {"url": "https://veklom.com/pricing", "page": "Pricing"},
    {"url": "https://veklom.com/docs", "page": "Docs"},
]

TARGET_KEYWORDS = [
    "sovereign ai platform",
    "langchain governance",
    "enterprise ai control plane",
    "self-hosted llm infrastructure",
    "ai audit trail",
    "byok ai platform",
    "mcp server python",
    "multi-provider llm routing",
    "ai agent orchestration platform",
    "llm cost optimization enterprise",
]


# ── Utilities ─────────────────────────────────────────────────────────────────
def log_activity(event_type: str, data: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "040-seo",
        "event": event_type,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{entry['timestamp']}] [{event_type}] {data.get('message', '')[:80]}")


# ── Page Audit ────────────────────────────────────────────────────────────────
def audit_page(page_info: dict) -> dict:
    result = {"url": page_info["url"], "page": page_info["page"], "issues": [], "signals": {}}
    try:
        resp = requests.get(page_info["url"], timeout=10, headers={"User-Agent": "VeklomSEOAudit/1.0"})
        result["signals"]["status_code"] = resp.status_code
        result["signals"]["response_time_ms"] = int(resp.elapsed.total_seconds() * 1000)

        html = resp.text

        # Check title tag
        import re
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            result["signals"]["title"] = title
            result["signals"]["title_length"] = len(title)
            if len(title) < 30:
                result["issues"].append("Title too short (<30 chars)")
            elif len(title) > 65:
                result["issues"].append("Title too long (>65 chars)")
        else:
            result["issues"].append("Missing <title> tag")

        # Check meta description
        meta_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
        if meta_match:
            desc = meta_match.group(1)
            result["signals"]["meta_description_length"] = len(desc)
            if len(desc) < 120:
                result["issues"].append("Meta description too short (<120 chars)")
        else:
            result["issues"].append("Missing meta description")

        # Check H1
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            result["signals"]["h1"] = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()[:100]
        else:
            result["issues"].append("Missing H1 tag")

        if resp.status_code != 200:
            result["issues"].append(f"Non-200 status: {resp.status_code}")

    except Exception as e:
        result["issues"].append(f"Audit failed: {str(e)}")

    return result


# ── SEO Recommendations ───────────────────────────────────────────────────────
def generate_keyword_recommendations() -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert SEO strategist specialising in B2B SaaS and developer tools. "
                    "Generate specific, actionable SEO recommendations. Be concrete — give exact copy, not vague advice."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Product: Veklom — sovereign AI control plane for enterprises. Website: https://veklom.com\n\n"
                    f"Target keywords: {json.dumps(TARGET_KEYWORDS, indent=2)}\n\n"
                    "Generate:\n"
                    "1. Top 5 highest-opportunity long-tail keywords with estimated search intent\n"
                    "2. Recommended page titles (60 chars max) for Homepage, Pricing, and Docs pages\n"
                    "3. Recommended meta descriptions (155 chars max) for those same pages\n"
                    "4. 3 blog post title ideas that could rank for these keywords\n"
                    "5. Internal linking recommendations\n"
                ),
            },
        ],
        max_tokens=1000,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


# ── Report Generation ─────────────────────────────────────────────────────────
def generate_report(audit_results: list, recommendations: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = REPORT_DIR / f"seo_report_{date_str}.md"

    with open(filename, "w") as f:
        f.write(f"# Veklom SEO Report — {date_str}\n\n")
        f.write("## Page Audit Results\n\n")

        for result in audit_results:
            f.write(f"### {result['page']} ({result['url']})\n\n")
            if result["signals"]:
                f.write("**Signals:**\n")
                for k, v in result["signals"].items():
                    f.write(f"- {k}: {v}\n")
                f.write("\n")
            if result["issues"]:
                f.write("**Issues:**\n")
                for issue in result["issues"]:
                    f.write(f"- ⚠️ {issue}\n")
                f.write("\n")
            else:
                f.write("✅ No issues found\n\n")

        f.write("## Keyword & Copy Recommendations\n\n")
        f.write(recommendations)
        f.write("\n")

    return filename


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"=== Veklom Agent 040 — SEO Intelligence === {datetime.now().isoformat()}")

    print("Auditing Veklom pages...")
    audit_results = []
    for page in VEKLOM_PAGES:
        print(f"  Auditing {page['url']}...")
        result = audit_page(page)
        audit_results.append(result)
        issue_count = len(result["issues"])
        print(f"  → {issue_count} issue(s) found")

    print("Generating keyword recommendations...")
    recommendations = generate_keyword_recommendations()

    report_path = generate_report(audit_results, recommendations)
    print(f"\nReport saved: {report_path}")

    log_activity("REPORT_GENERATED", {
        "message": f"SEO report generated: {report_path}",
        "pages_audited": len(audit_results),
        "total_issues": sum(len(r["issues"]) for r in audit_results),
    })

    print("=== Agent 040 complete ===")
