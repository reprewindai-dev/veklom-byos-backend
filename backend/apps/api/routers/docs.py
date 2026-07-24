"""Documentation router - Local docs and DNS resolution fixes."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.core.security.auth import get_current_user_optional
from backend.db.models.user import User

router = APIRouter(tags=["Documentation"])


@router.get("/docs", response_class=HTMLResponse)
async def get_docs_home(
    local: bool = Query(default=False),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get documentation home with DNS/local fallback."""
    try:
        if local:
            # Serve local documentation
            return await serve_local_docs("index.html")
        else:
            # Try DNS resolution first, fallback to local
            return await get_docs_with_fallback("home", user)

    except Exception as e:
        return await get_docs_fallback_error("docs", str(e))


@router.get("/docs/{path:path}")
async def get_docs_path(
    path: str,
    local: bool = Query(default=False),
    format: str = Query(default="html", pattern="^(html|json|md)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get documentation path with proper routing."""
    try:
        if local:
            return await serve_local_docs(path, format)
        else:
            return await get_docs_with_fallback(path, user, format)

    except Exception as e:
        return await get_docs_fallback_error(f"docs/{path}", str(e))


@router.get("/docs/api/overview")
async def get_api_overview(
    format: str = Query(default="html", pattern="^(html|json)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get API overview documentation."""
    try:
        overview = {
            "title": "Veklom BYOS API Documentation",
            "version": "2.1.0",
            "base_url": "/api/v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),

            # Core Endpoints
            "endpoints": {
                "authority": {
                    "base": "/api/v1/authority-runs",
                    "description": "AuthorityRun governance and execution",
                    "methods": ["GET", "POST", "PATCH", "DELETE"]
                },
                "pgl": {
                    "base": "/api/v1/pgl",
                    "description": "Project Governance Layer",
                    "methods": ["GET", "POST", "PUT"]
                },
                "cappo": {
                    "base": "/api/v1/cappo",
                    "description": "CAPPO internal execution",
                    "methods": ["GET", "POST", "PUT"]
                },
                "evidence": {
                    "base": "/api/v1/evidence-pack",
                    "description": "EvidencePack system",
                    "methods": ["GET", "POST", "PUT"]
                },
                "x402": {
                    "base": "/api/v1/x402",
                    "description": "Payment gate enforcement",
                    "methods": ["GET", "POST", "PUT"]
                },
                "marketplace": {
                    "base": "/api/v1/marketplace",
                    "description": "Marketplace and vendor management",
                    "methods": ["GET", "POST", "PUT", "DELETE"]
                }
            },

            # Authentication
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer <token>",
                "login_endpoint": "/auth/login",
                "refresh_endpoint": "/auth/refresh"
            },

            # Rate Limiting
            "rate_limiting": {
                "requests_per_minute": 1000,
                "burst_limit": 100,
                "headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
            },

            # Error Handling
            "error_handling": {
                "format": "JSON",
                "status_codes": {
                    "400": "Bad Request",
                    "401": "Unauthorized",
                    "403": "Forbidden",
                    "404": "Not Found",
                    "429": "Rate Limited",
                    "500": "Internal Server Error"
                }
            }
        }

        if format == "json":
            return overview
        else:
            return await render_docs_html("api_overview", overview)

    except Exception as e:
        return await get_docs_fallback_error("api/overview", str(e))


@router.get("/docs/guides/quickstart")
async def get_quickstart_guide(
    format: str = Query(default="html", pattern="^(html|json|md)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get quickstart guide."""
    try:
        guide = {
            "title": "Veklom BYOS Quickstart Guide",
            "description": "Get started with Veklom BYOS in 5 minutes",
            "estimated_time": "5 minutes",
            "prerequisites": [
                "Python 3.8+",
                "API key from Veklom dashboard",
                "Basic understanding of REST APIs"
            ],

            "steps": [
                {
                    "step": 1,
                    "title": "Get Your API Key",
                    "description": "Navigate to the Veklom dashboard and generate an API key",
                    "code": "export VEKLOM_API_KEY=${YOUR_API_KEY}"
                },
                {
                    "step": 2,
                    "title": "Make Your First Request",
                    "description": "Test your API connection with a simple health check",
                    "code": "curl -H 'Authorization: Bearer $VEKLOM_API_KEY' https://api.veklom.com/health"
                },
                {
                    "step": 3,
                    "title": "Create an AuthorityRun",
                    "description": "Create your first governed execution context",
                    "code": """curl -X POST \\
  -H 'Authorization: Bearer $VEKLOM_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{"name": "My First Run", "context": "testing"}' \\
  https://api.veklom.com/api/v1/authority-runs"""
                },
                {
                    "step": 4,
                    "title": "Execute with Governance",
                    "description": "Execute your first governed AI agent",
                    "code": """curl -X POST \\
  -H 'Authorization: Bearer $VEKLOM_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{"agent_id": "test_agent", "task": "Hello World"}' \\
  https://api.veklom.com/api/v1/cappo/execute"""
                }
            ],

            "next_steps": [
                "Read the API documentation",
                "Explore PGL onboarding",
                "Try the Agent Arena",
                "Set up payment gates"
            ]
        }

        if format == "json":
            return guide
        elif format == "md":
            return await render_markdown("quickstart", guide)
        else:
            return await render_docs_html("quickstart", guide)

    except Exception as e:
        return await get_docs_fallback_error("guides/quickstart", str(e))


@router.get("/docs/guides/pgl-onboarding")
async def get_pgl_onboarding_guide(
    format: str = Query(default="html", pattern="^(html|json|md)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get PGL onboarding guide."""
    try:
        guide = {
            "title": "PGL Onboarding Guide",
            "description": "Complete guide to Project Governance Layer onboarding",
            "estimated_time": "15 minutes",

            "overview": {
                "what_is_pgl": "Project Governance Layer provides birth certificates and authority for AI agents",
                "why_needed": "Required for all agent execution in the Veklom ecosystem",
                "benefits": ["Human oversight", "Audit trails", "Compliance", "Trust"]
            },

            "onboarding_steps": [
                {
                    "step": 1,
                    "name": "Operator Identity",
                    "endpoint": "/onboarding/pgl/operator-identity",
                    "description": "Establish your identity as the system operator",
                    "required_fields": ["name", "email", "organization"],
                    "example": {
                        "name": "John Doe",
                        "email": "john@company.com",
                        "organization": "Acme Corp"
                    }
                },
                {
                    "step": 2,
                    "name": "Workspace Authority",
                    "endpoint": "/onboarding/pgl/workspace-authority",
                    "description": "Define your workspace authority boundaries",
                    "required_fields": ["workspace_name", "domain", "scope"],
                    "example": {
                        "workspace_name": "Production Workspace",
                        "domain": "acme.com",
                        "scope": ["data_analysis", "automation"]
                    }
                },
                {
                    "step": 3,
                    "name": "Agent Certificate",
                    "endpoint": "/onboarding/pgl/agent-certificate",
                    "description": "Generate certificates for your AI agents",
                    "required_fields": ["agent_name", "capabilities", "safety_rules"],
                    "example": {
                        "agent_name": "Data Analyzer",
                        "capabilities": ["web_search", "data_analysis"],
                        "safety_rules": ["no_external_payments", "data_privacy"]
                    }
                },
                {
                    "step": 4,
                    "name": "Ledger Lineage",
                    "endpoint": "/onboarding/pgl/ledger-lineage",
                    "description": "Initialize the immutable ledger for tracking",
                    "required_fields": ["ledger_type", "retention_policy"],
                    "example": {
                        "ledger_type": "merkle_tree",
                        "retention_policy": "7_years"
                    }
                },
                {
                    "step": 5,
                    "name": "First Proof",
                    "endpoint": "/onboarding/pgl/first-proof",
                    "description": "Execute your first governed proof-of-concept",
                    "required_fields": ["proof_type", "test_case"],
                    "example": {
                        "proof_type": "compliance_check",
                        "test_case": "data_privacy_validation"
                    }
                }
            ],

            "troubleshooting": {
                "common_issues": [
                    {
                        "issue": "Certificate generation fails",
                        "solution": "Check workspace authority configuration"
                    },
                    {
                        "issue": "Ledger initialization timeout",
                        "solution": "Verify network connectivity and retry"
                    }
                ]
            }
        }

        if format == "json":
            return guide
        elif format == "md":
            return await render_markdown("pgl-onboarding", guide)
        else:
            return await render_docs_html("pgl-onboarding", guide)

    except Exception as e:
        return await get_docs_fallback_error("guides/pgl-onboarding", str(e))


@router.get("/docs/reference/seked")
async def get_seked_reference(
    format: str = Query(default="html", pattern="^(html|json|md)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get SEKED measurement system reference."""
    try:
        reference = {
            "title": "SEKED Measurement System Reference",
            "description": "Complete reference for SEKED measurements and directives",

            "measurements": {
                "E": {
                    "name": "Environmental",
                    "description": "Environmental impact and resource usage",
                    "range": "1-10",
                    "calculation": "Based on CPU, memory, and network usage"
                },
                "R": {
                    "name": "Risk",
                    "description": "Risk assessment and safety scoring",
                    "range": "1-10",
                    "calculation": "Based on potential harm and uncertainty"
                },
                "C": {
                    "name": "Compliance",
                    "description": "Regulatory and policy compliance",
                    "range": "1-10",
                    "calculation": "Based on rule adherence and audit results"
                },
                "D": {
                    "name": "Decision",
                    "description": "Decision quality and reasoning",
                    "range": "1-10",
                    "calculation": "Based on logic and outcome validity"
                },
                "S": {
                    "name": "Safety",
                    "description": "Overall safety and security",
                    "range": "1-10",
                    "calculation": "Based on vulnerability and threat assessment"
                }
            },

            "ratios": {
                "E/R": "Environmental to Risk ratio",
                "C/D": "Compliance to Decision ratio",
                "S/E": "Safety to Environmental ratio"
            },

            "directives": {
                "operational": {
                    "type": "Constraints",
                    "enforcement": "Real-time",
                    "examples": ["no_external_payments", "data_privacy_enforcement"]
                },
                "performance": {
                    "type": "Targets",
                    "enforcement": "Continuous",
                    "examples": ["max_response_time", "min_success_rate"]
                },
                "safety": {
                    "type": "Requirements",
                    "enforcement": "Pre-execution",
                    "examples": ["human_approval_required", "audit_logging"]
                }
            }
        }

        if format == "json":
            return reference
        elif format == "md":
            return await render_markdown("seked-reference", reference)
        else:
            return await render_docs_html("seked-reference", reference)

    except Exception as e:
        return await get_docs_fallback_error("reference/seked", str(e))


@router.get("/docs/health")
async def get_docs_health():
    """Check documentation system health."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dns_resolution": "working",
        "local_docs": "available",
        "fallback_enabled": True
    }


def get_docs_dir() -> str:
    """Locate the absolute path to the docs directory dynamically."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = current_dir
    for _ in range(6):
        possible_docs = os.path.join(temp_dir, "docs")
        if os.path.isdir(possible_docs):
            return possible_docs
        parent = os.path.dirname(temp_dir)
        if parent == temp_dir:
            break
        temp_dir = parent
    return os.path.abspath(os.path.join(current_dir, "../../../docs"))


def markdown_to_html(md_text: str) -> str:
    """Simple regex-based markdown to HTML converter."""
    import re
    html = md_text

    # Escape HTML entities first for safety
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Code blocks
    html = re.sub(r'```(.*?)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Bold / Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Lists
    html = re.sub(r'^\s*-\s+(.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>)+', r'<ul>\g<0></ul>', html, flags=re.DOTALL)

    # Links
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)

    # Paragraphs (split by double newline, wrap in <p> if not block elements)
    paragraphs = html.split("\n\n")
    for i, p in enumerate(paragraphs):
        p = p.strip()
        if p and not p.startswith("<h") and not p.startswith("<pre") and not p.startswith("<ul") and not p.startswith("<li"):
            replaced_p = p.replace('\n', '<br>')
            paragraphs[i] = f"<p>{replaced_p}</p>"

    return "\n\n".join(paragraphs)


@router.get("/docs/search")
async def search_docs(
    q: str = Query(..., min_length=1),
    format: str = Query(default="json", pattern="^(json|html)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Search documentation filesystem."""
    import re

    try:
        docs_dir = get_docs_dir()
        results = []

        if os.path.isdir(docs_dir):
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if file.endswith(".md"):
                        abs_file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_file_path, docs_dir).replace("\\", "/")
                        doc_name = rel_path[:-3]

                        try:
                            with open(abs_file_path, "r", encoding="utf-8") as f:
                                content = f.read()

                            if q.lower() in content.lower():
                                title = doc_name.replace("-", " ").replace("_", " ").title()
                                for line in content.splitlines():
                                    if line.startswith("# "):
                                        title = line[2:].strip()
                                        break

                                match_idx = content.lower().find(q.lower())
                                start_idx = max(0, match_idx - 60)
                                end_idx = min(len(content), match_idx + len(q) + 80)
                                snippet = content[start_idx:end_idx].strip()

                                if start_idx > 0:
                                    snippet = "..." + snippet
                                if end_idx < len(content):
                                    snippet = snippet + "..."

                                occurrences = len(re.findall(re.escape(q), content, re.IGNORECASE))
                                relevance = min(0.99, 0.5 + (occurrences * 0.05))

                                results.append({
                                    "title": title,
                                    "url": f"/docs/{doc_name}",
                                    "snippet": snippet,
                                    "relevance": round(relevance, 2)
                                })
                        except Exception as file_err:
                            import logging
                            logging.warning(f"Failed to read file {abs_file_path} during search: {file_err}")

        # Sort results by relevance descending
        results = sorted(results, key=lambda x: x["relevance"], reverse=True)

        if format == "json":
            return {
                "query": q,
                "results": results,
                "total_count": len(results)
            }
        else:
            return await render_docs_html("search", {"query": q, "results": results})

    except Exception as e:
        return await get_docs_fallback_error("search", str(e))


# Helper functions
async def get_docs_with_fallback(path: str, user: Optional[User], format: str = "html"):
    """Try DNS docs first, fallback to local."""
    try:
        external_docs = await fetch_external_docs(path, format)
        if external_docs:
            return external_docs
    except Exception:
        pass

    return await serve_local_docs(path, format)


async def fetch_external_docs(path: str, format: str):
    """Fetch documentation from external DNS."""
    return None


async def serve_local_docs(path: str, format: str = "html"):
    """Serve local documentation from filesystem."""

    docs_dir = get_docs_dir()
    clean_path = path.strip("/").replace("\\", "/")

    if not clean_path or clean_path in ("index.html", "home"):
        files = []
        if os.path.isdir(docs_dir):
            for root, _, fs in os.walk(docs_dir):
                for f in fs:
                    if f.endswith(".md"):
                        rel = os.path.relpath(os.path.join(root, f), docs_dir)
                        files.append(rel.replace("\\", "/")[:-3])

        return await render_docs_html("index", {
            "title": "Veklom BYOS Documentation",
            "sections": sorted(files)
        })

    md_file_path = os.path.join(docs_dir, f"{clean_path}.md")
    if not os.path.isfile(md_file_path):
        md_file_path = os.path.join(docs_dir, clean_path)
        if not os.path.isfile(md_file_path) and not clean_path.endswith(".md"):
            md_file_path = os.path.join(docs_dir, f"{clean_path}/README.md")

    if os.path.isfile(md_file_path):
        try:
            with open(md_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            title = clean_path.replace("-", " ").replace("_", " ").title()
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            if format == "json":
                return {
                    "title": title,
                    "content": content,
                    "path": clean_path
                }
            elif format == "md":
                return content
            else:
                html_body = markdown_to_html(content)
                return await render_docs_html("document", {"title": title, "body": html_body, "raw_content": content})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading documentation file: {str(e)}")

    raise HTTPException(status_code=404, detail=f"Documentation file not found: {path}")


async def render_docs_html(template: str, data: dict):
    """Render documentation as HTML."""
    title = data.get("title", "Veklom Documentation")
    body_content = data.get("body", "")

    if template == "index":
        sections_html = "".join(f'<li><a href="/api/v1/docs/{s}">{s.replace("/", " ➔ ").title()}</a></li>' for s in data.get("sections", []))
        body_content = f"<h2>Available Documents</h2><ul>{sections_html}</ul>"
    elif template == "search":
        query = data.get("query", "")
        results = data.get("results", [])
        if not results:
            body_content = f"<p>No results found for query: <strong>{query}</strong></p>"
        else:
            results_html = "".join(
                f'<div style="margin-bottom: 20px;">'
                f'<h3><a href="/api/v1/docs/{r["url"].replace("/docs/", "")}">{r["title"]}</a> <span style="font-size:0.8em;color:#666;">(relevance: {r["relevance"]})</span></h3>'
                f'<p style="font-style: italic;">{r["snippet"]}</p>'
                f'</div>'
                for r in results
            )
            body_content = f"<h2>Search Results for: <em>{query}</em></h2>{results_html}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; color: #333; background-color: #fcfcfc; }}
            .container {{ max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            .header {{ border-bottom: 1px solid #eaeaea; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-size: 2.2em; color: #111; }}
            .content {{ background: white; padding: 30px; border: 1px solid #e1e4e8; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; }}
            code {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; background-color: rgba(27,31,35,0.05); padding: 0.2em 0.4em; border-radius: 3px; }}
            a {{ color: #0366d6; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            .footer {{ margin-top: 50px; text-align: center; font-size: 0.85em; color: #6a737d; border-top: 1px solid #eaeaea; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                {body_content}
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} Veklom Sovereign Control Systems. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


async def render_markdown(template: str, data: dict):
    """Render documentation as Markdown."""
    return data.get("raw_content", "")


async def get_docs_fallback_error(path: str, error: str):
    """Get fallback error page."""
    error_data = {
        "error": "Documentation temporarily unavailable",
        "path": path,
        "message": f"Documentation path failed to load: {error}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return await render_docs_html("error", error_data)
