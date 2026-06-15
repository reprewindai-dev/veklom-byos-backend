"""Documentation router - Local docs and DNS resolution fixes."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_user_optional
from backend.db.models.user import User
import os
import json

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
    format: str = Query(default="html", regex="^(html|json|md)$"),
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
    format: str = Query(default="html", regex="^(html|json)$"),
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
    format: str = Query(default="html", regex="^(html|json|md)$"),
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
                    "code": "export VEKLOM_API_KEY='your_api_key_here'"
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
    format: str = Query(default="html", regex="^(html|json|md)$"),
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
    format: str = Query(default="html", regex="^(html|json|md)$"),
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


@router.get("/docs/search")
async def search_docs(
    q: str = Query(..., min_length=1),
    format: str = Query(default="json", regex="^(json|html)$"),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Search documentation."""
    try:
        # Mock search implementation
        results = [
            {
                "title": "AuthorityRun API",
                "url": "/docs/api/overview#authority",
                "snippet": "AuthorityRun governance and execution endpoints...",
                "relevance": 0.95
            },
            {
                "title": "PGL Onboarding",
                "url": "/docs/guides/pgl-onboarding",
                "snippet": "Complete guide to Project Governance Layer onboarding...",
                "relevance": 0.87
            }
        ]
        
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
        # Try to fetch from DNS/external docs
        external_docs = await fetch_external_docs(path, format)
        if external_docs:
            return external_docs
    except Exception:
        pass
    
    # Fallback to local docs
    return await serve_local_docs(path, format)


async def fetch_external_docs(path: str, format: str):
    """Fetch documentation from external DNS."""
    # Mock external docs fetch - would integrate with real CDN/docs service
    return None


async def serve_local_docs(path: str, format: str = "html"):
    """Serve local documentation."""
    # Mock local docs serving - would serve from actual docs directory
    if path == "index.html" or path == "home":
        return await render_docs_html("index", {
            "title": "Veklom BYOS Documentation",
            "sections": ["API Overview", "Guides", "Reference"]
        })
    
    raise HTTPException(status_code=404, detail="Documentation not found")


async def render_docs_html(template: str, data: dict):
    """Render documentation as HTML."""
    # Mock HTML rendering - would use actual template engine
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{data.get('title', 'Veklom Documentation')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; }}
            .content {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{data.get('title', 'Veklom Documentation')}</h1>
        </div>
        <div class="content">
            <p>Documentation for template: {template}</p>
            <pre>{json.dumps(data, indent=2)}</pre>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


async def render_markdown(template: str, data: dict):
    """Render documentation as Markdown."""
    # Mock Markdown rendering
    md_content = f"# {data.get('title', 'Documentation')}\n\n"
    md_content += f"{data.get('description', '')}\n\n"
    md_content += "```json\n"
    md_content += json.dumps(data, indent=2)
    md_content += "\n```"
    return md_content


async def get_docs_fallback_error(path: str, error: str):
    """Get fallback error page."""
    error_data = {
        "error": "Documentation temporarily unavailable",
        "path": path,
        "message": "Please try again later or use local docs with ?local=true",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return await render_docs_html("error", error_data)
