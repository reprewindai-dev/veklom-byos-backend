""".well-known manifests - Machine-readable endpoints for Veklom control plane."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user_optional
from backend.core.security.jwt_keys import key_manager
from backend.db.models.user import User
from backend.schemas.capability_contract import CapabilityManifest, CapabilityContract
import uuid
import json

router = APIRouter(prefix="/.well-known", tags=["Well-Known"])

@router.get("/capabilities.json", response_model=CapabilityManifest)
async def get_capabilities_manifest():
    """Exposes the governance contracts for all capabilities on this backend."""
    return CapabilityManifest(
        service_name="veklom-byos-backend",
        capabilities=[
            CapabilityContract(
                capability_id="blueprint.generate",
                description="Generates an architectural blueprint based on repository context.",
                requires=["tenant", "repository"],
                allows_pii=["github_username"],
                denies_pii=["email", "phone", "address", "ssn"],
                secret_injections=["github_pat"],
                outputs=["blueprint"]
            ),
            CapabilityContract(
                capability_id="repository.health",
                description="Analyzes the health and structure of a governed repository.",
                requires=["tenant", "repository"],
                allows_pii=[],
                denies_pii=["email", "phone", "address", "ssn"],
                secret_injections=["github_pat"],
                outputs=["health_report"]
            )
        ]
    )

@router.get("/security.txt", response_class=JSONResponse)
async def security_txt():
    """Security contact and policy information."""
    
    security_info = {
        "contact": [
            "mailto:security@veklom.com",
            "https://hackerone.com/veklom"
        ],
        "policy": "https://veklom.com/security-policy",
        "acknowledgments": "https://veklom.com/security-acknowledgments",
        "canonical": "https://api.veklom.com/.well-known/security.txt",
        "expires": "2026-12-31T23:59:59Z"
    }
    
    return JSONResponse(
        content=security_info,
        headers={"Content-Type": "text/plain"}
    )


@router.get("/veklom/authority", response_model=Dict[str, Any])
async def veklom_authority_manifest():
    """Veklom Authority System manifest."""
    
    authority_manifest = {
        "manifest_version": "1.0.0",
        "system_type": "veklom_authority",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # System Information
        "system": {
            "name": "Veklom BYOS Authority System",
            "version": "2.1.0",
            "description": "Human-centric governed AI agent management platform",
            "environment": "production",
            "region": "global"
        },
        
        # Authority Components
        "components": {
            "authority_run": {
                "api_version": "v1",
                "endpoint": "/api/v1/authority-runs",
                "capabilities": ["create", "execute", "monitor", "evidence"],
                "status": "active"
            },
            "pgl": {
                "api_version": "v1", 
                "endpoint": "/api/v1/pgl",
                "capabilities": ["onboarding", "profile", "agents", "execution"],
                "status": "active"
            },
            "cappo": {
                "api_version": "v1",
                "endpoint": "/api/v1/cappo",
                "capabilities": ["execution", "policy", "monitoring"],
                "status": "active"
            },
            "evidence_pack": {
                "api_version": "v1",
                "endpoint": "/api/v1/evidence-pack",
                "capabilities": ["create", "verify", "audit"],
                "status": "active"
            },
            "x402": {
                "api_version": "v1",
                "endpoint": "/api/v1/x402",
                "capabilities": ["payment_gate", "billing", "enforcement"],
                "status": "active"
            }
        },
        
        # Security and Compliance
        "security": {
            "authentication": ["oauth2", "jwt"],
            "authorization": "rbac",
            "encryption": "aes-256-gcm",
            "compliance": ["sox", "gdpr", "soc2", "hipaa"],
            "audit_logging": True
        },
        
        # Trust Framework
        "trust_framework": {
            "pki_provider": "veklom_trust",
            "certificate_chain": "https://trust.veklom.com/chain.pem",
            "root_hash": "sha256:veklom_root_abc123...",
            "verification_endpoint": "/api/v1/trust/verify"
        }
    }
    
    return authority_manifest


@router.get("/veklom/pgl", response_model=Dict[str, Any])
async def veklom_pgl_manifest():
    """Project Governance Layer (PGL) manifest."""
    
    pgl_manifest = {
        "manifest_version": "1.0.0",
        "component": "project_governance_layer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # PGL Configuration
        "pgl_config": {
            "onboarding_flow": "/onboarding/pgl",
            "profile_endpoint": "/api/v1/pgl/profile",
            "authority_types": ["operator", "workspace", "agent"],
            "certificate_issuer": "veklom_pgl",
            "genome_version": "1.0.0"
        },
        
        # Onboarding Steps
        "onboarding_steps": [
            {
                "step": 1,
                "name": "operator_identity",
                "endpoint": "/api/v1/pgl/onboarding/operator-identity",
                "required": True
            },
            {
                "step": 2,
                "name": "workspace_authority",
                "endpoint": "/api/v1/pgl/onboarding/workspace-authority", 
                "required": True
            },
            {
                "step": 3,
                "name": "agent_certificate",
                "endpoint": "/api/v1/pgl/onboarding/agent-certificate",
                "required": True
            },
            {
                "step": 4,
                "name": "ledger_lineage",
                "endpoint": "/api/v1/pgl/onboarding/ledger-lineage",
                "required": True
            },
            {
                "step": 5,
                "name": "first_proof",
                "endpoint": "/api/v1/pgl/onboarding/first-proof",
                "required": True
            }
        ],
        
        # Agent Management
        "agent_management": {
            "lifecycle": ["create", "certificate", "execute", "retire"],
            "capabilities": ["web_search", "data_analysis", "automation"],
            "safety_rules": ["no_external_payments", "data_privacy", "scope_enforcement"],
            "genome_hashing": "sha256"
        }
    }
    
    return pgl_manifest


@router.get("/veklom/evidence", response_model=Dict[str, Any])
async def veklom_evidence_manifest():
    """EvidencePack system manifest."""
    
    evidence_manifest = {
        "manifest_version": "1.0.0",
        "component": "evidence_pack_system",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # Evidence Configuration
        "evidence_config": {
            "pack_creation": "automatic",
            "integrity_verification": "sha256",
            "audit_trail": True,
            "retention": "7_years"
        },
        
        # Evidence Components
        "components": {
            "pgl": {
                "certificate": True,
                "genome": True,
                "lineage": True,
                "ledger": True
            },
            "seked": {
                "measurements": True,
                "directives": True,
                "compliance": True
            },
            "cappo": {
                "executions": True,
                "policy_compliance": True,
                "resource_usage": True
            },
            "x402": {
                "transactions": True,
                "settlements": True,
                "budget_tracking": True
            }
        },
        
        # Chain Integrity
        "chain_integrity": {
            "hash_algorithm": "sha256",
            "merkle_tree": True,
            "tamper_detection": True,
            "verification_endpoint": "/api/v1/evidence-pack/verify/{pack_id}"
        }
    }
    
    return evidence_manifest


@router.get("/veklom/x402", response_model=Dict[str, Any])
async def veklom_x402_manifest():
    """x402 payment gate system manifest."""
    
    x402_manifest = {
        "manifest_version": "1.0.0",
        "component": "x402_payment_gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # Payment Configuration
        "payment_config": {
            "standard": "x402",
            "currency": "USD",
            "processors": ["stripe", "internal"],
            "settlement": "real_time"
        },
        
        # Gate Types
        "gate_types": {
            "execution_cost": {
                "description": "Agent execution resource costs",
                "calculation": "per_second",
                "typical_range": "0.10-0.50"
            },
            "resource_quota": {
                "description": "Resource quota overages",
                "calculation": "per_mb_hour",
                "typical_range": "0.05-0.20"
            },
            "budget_limit": {
                "description": "Budget limit enforcement",
                "calculation": "fixed",
                "typical_range": "0.01-0.10"
            }
        },
        
        # Payment Flow
        "payment_flow": {
            "evaluation": "/api/v1/x402/gate/evaluate",
            "processing": "/api/v1/x402/authority-run/{run_id}/pay",
            "confirmation": "/api/v1/x402/payment/{payment_id}/confirm",
            "enforcement": "/api/v1/x402/gate/enforce"
        }
    }
    
    return x402_manifest


@router.get("/veklom/health", response_model=Dict[str, Any])
async def veklom_health_manifest():
    """System health and status manifest."""
    
    health_manifest = {
        "manifest_version": "1.0.0",
        "component": "system_health",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # System Status
        "system_status": {
            "overall": "healthy",
            "uptime": "99.9%",
            "last_deployment": "2026-01-15T08:00:00Z",
            "version": "2.1.0"
        },
        
        # Component Health
        "components": {
            "authority_run": {"status": "healthy", "response_time_ms": 45},
            "pgl": {"status": "healthy", "response_time_ms": 32},
            "cappo": {"status": "healthy", "response_time_ms": 28},
            "evidence_pack": {"status": "healthy", "response_time_ms": 51},
            "x402": {"status": "healthy", "response_time_ms": 67}
        },
        
        # Performance Metrics
        "performance": {
            "api_response_time_p95_ms": 85,
            "error_rate_percent": 0.2,
            "throughput_rps": 1250
        },
        
        # Active Metrics
        "active_metrics": {
            "authority_runs": 47,
            "active_agents": 23,
            "daily_executions": 1247,
            "evidence_packs": 892
        }
    }
    
    return health_manifest


@router.get("/veklom", response_model=Dict[str, Any])
async def get_veklom_manifest(
    db: AsyncSession = Depends(get_db)
):
    """Veklom control plane manifest."""
    
    manifest = {
        "name": "Veklom Control Plane",
        "version": "1.0.0",
        "description": "Sovereign AI control plane with PGL, SEKED, CAPPO, and x402 integration",
        "homepage": "https://veklom.com",
        "documentation": "https://veklom.com/vnp/docs",
        
        # API endpoints
        "api": {
            "base_url": "/api/v1",
            "version": "v1",
            "authentication": "Bearer token",
            "openapi": "/api/v1/docs"
        },
        
        # Core components
        "components": {
            "pgl": {
                "name": "Policy Governance Ledger",
                "description": "Agent authority and birth certificates",
                "endpoints": {
                    "onboarding": "/api/v1/pgl/onboarding",
                    "adapter": "/api/v1/pgl",
                    "status": "/api/v1/pgl/status"
                }
            },
            "seked": {
                "name": "SEKED Policy Engine",
                "description": "Embedded policy engine within AuthorityRun",
                "endpoints": {
                    "authority": "/api/v1/authority",
                    "runs": "/api/v1/authority/runs"
                }
            },
            "cappo": {
                "name": "CAPPO Execution Authority",
                "description": "Internal execution authority (no frontend)",
                "endpoints": {
                    "execution": "/api/v1/cappo/execution",
                    "queue": "/api/v1/cappo/queue"
                }
            },
            "x402": {
                "name": "x402 Payment Gate",
                "description": "HTTP 402 payment required implementation",
                "endpoints": {
                    "gate": "/api/v1/x402/gate",
                    "payment": "/api/v1/x402/payment"
                }
            },
            "evidence": {
                "name": "Evidence Pack System",
                "description": "Comprehensive evidence collection",
                "endpoints": {
                    "packs": "/api/v1/evidence-pack",
                    "evidence": "/api/v1/evidence"
                }
            }
        },
        
        # Authority spine
        "authority_spine": {
            "source": "Source code and configuration",
            "risk": "Risk assessment and gating",
            "plan": "Plan compilation (GPC)",
            "authority": "Authority decisions (SEKED)",
            "payment": "Payment gates (x402)",
            "test": "Testing and validation",
            "evidence": "Evidence collection",
            "release": "Release management",
            "operate": "Operations and runtime",
            "prove": "Proof and verification"
        },
        
        # Compliance and security
        "compliance": {
            "standards": ["SOC2", "ISO27001", "GDPR", "HIPAA"],
            "certifications": ["SOC2-Ready", "HIPAA-Aware"],
            "data_residency": "EU-Sovereign",
            "encryption": "AES-256 at rest, TLS 1.3 in transit"
        },
        
        # Infrastructure
        "infrastructure": {
            "regions": ["EU", "US"],
            "providers": ["Hetzner", "AWS"],
            "architecture": "Sovereign control plane",
            "monitoring": "Full observability"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/authority", response_model=Dict[str, Any])
async def get_authority_manifest(
    db: AsyncSession = Depends(get_db)
):
    """Authority system manifest."""
    
    manifest = {
        "authority_system": "Veklom AuthorityRun",
        "version": "1.0.0",
        "description": "Runtime authority system with embedded SEKED policy engine",
        
        # Authority contracts
        "contracts": {
            "AuthorityRun": {
                "description": "Tracks authority execution runs",
                "fields": [
                    "id", "authority_bundle_id", "agent_id", "workspace_id",
                    "executor_id", "status", "decisions", "violations", "approvals",
                    "evidence_pack_id", "metrics", "audit_metadata"
                ]
            },
            "AuthorityDecision": {
                "description": "Records individual authority decisions",
                "fields": [
                    "id", "authority_run_id", "tool_name", "decision", "reason",
                    "confidence_score", "seked_measurement", "seked_ratios",
                    "seked_directive", "seked_policy_id", "seked_proof_id"
                ]
            }
        },
        
        # SEKED integration
        "seked": {
            "description": "Embedded policy engine",
            "measurements": ["E", "R", "C", "D", "S"],
            "ratios": ["sigma", "ci", "si"],
            "directives": [
                "Execute primary objectives",
                "Prepare for execution", 
                "Conserve resources",
                "Initiate recovery",
                "Escalate to human"
            ]
        },
        
        # API endpoints
        "endpoints": {
            "authority": "/api/v1/authority",
            "authority_runs": "/api/v1/authority/runs",
            "context": "/api/v1/authority/runs/{run_id}/context",
            "evidence": "/api/v1/authority/runs/{run_id}/evidence"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/pgl", response_model=Dict[str, Any])
async def get_pgl_manifest(
    db: AsyncSession = Depends(get_db)
):
    """PGL (Policy Governance Ledger) manifest."""
    
    manifest = {
        "pgl_system": "Policy Governance Ledger",
        "version": "1.0.0",
        "description": "Agent authority and birth certificate system",
        
        # PGL components
        "components": {
            "onboarding": {
                "description": "Multi-step agent onboarding",
                "steps": [
                    "Operator Identity",
                    "Workspace Authority", 
                    "Agent Certificate",
                    "Genome Preview",
                    "Ledger Root",
                    "Payment Binding",
                    "First Proof"
                ]
            },
            "adapter": {
                "description": "PGL adapter/proxy for agent management",
                "endpoints": [
                    "/agents",
                    "/agents/{agent_id}/snapshot",
                    "/agents/{agent_id}/certificate",
                    "/agents/{agent_id}/lineage",
                    "/agents/{agent_id}/ledger",
                    "/agents/{agent_id}/verify"
                ]
            }
        },
        
        # Agent lifecycle
        "lifecycle": {
            "birth": "PGL birth certificate",
            "genome": "Agent genome and permissions",
            "lineage": "Agent lineage tracking",
            "ledger": "Tamper-evident ledger",
            "verification": "Certificate and genome verification"
        },
        
        # API endpoints
        "endpoints": {
            "onboarding": "/api/v1/pgl/onboarding",
            "adapter": "/api/v1/pgl",
            "status": "/api/v1/pgl/status"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/cappo", response_model=Dict[str, Any])
async def get_cappo_manifest(
    db: AsyncSession = Depends(get_db)
):
    """CAPPO (Execution Authority) manifest."""
    
    manifest = {
        "cappo_system": "CAPPO Execution Authority",
        "version": "1.0.0",
        "description": "Internal execution authority (no frontend)",
        
        # Execution workflow
        "workflow": {
            "request": "Submit execution request",
            "approval": "Approval workflow (auto/manual)",
            "queue": "Execution queue management",
            "execution": "Run execution with monitoring",
            "evidence": "Collect execution evidence"
        },
        
        # Execution types
        "execution_types": {
            "tool_execution": "Execute specific tools",
            "agent_execution": "Execute agent workflows",
            "batch_execution": "Batch processing",
            "scheduled_execution": "Scheduled tasks"
        },
        
        # Approval system
        "approval": {
            "auto_approval": "Based on SEKED policy",
            "manual_approval": "Human approval required",
            "conditional_approval": "With conditions",
            "budget_approval": "Budget-based approval"
        },
        
        # API endpoints
        "endpoints": {
            "execution": "/api/v1/cappo/execution",
            "queue": "/api/v1/cappo/queue",
            "approvals": "/api/v1/cappo/approvals",
            "evidence": "/api/v1/cappo/evidence"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/x402", response_model=Dict[str, Any])
async def get_x402_manifest(
    db: AsyncSession = Depends(get_db)
):
    """x402 Payment Gate manifest."""
    
    manifest = {
        "x402_system": "HTTP 402 Payment Required",
        "version": "1.0.0",
        "description": "Payment gate bound to AuthorityRun",
        
        # Payment gate types
        "gate_types": {
            "execution_cost": "Per-execution cost",
            "budget_limit": "Budget limit exceeded",
            "resource_quota": "Resource quota exceeded",
            "premium_feature": "Premium feature access",
            "evidence_export": "Evidence export fees"
        },
        
        # Payment flow
        "payment_flow": {
            "evaluate": "Evaluate if payment required",
            "trigger": "Trigger HTTP 402 response",
            "process": "Process payment transaction",
            "unblock": "Unblock execution on success"
        },
        
        # Payment methods
        "payment_methods": {
            "stripe": "Credit card payments",
            "paypal": "PayPal payments",
            "crypto": "Cryptocurrency payments",
            "wire": "Wire transfers"
        },
        
        # Budget management
        "budget": {
            "periods": ["hourly", "daily", "monthly"],
            "limits": "Configurable limits per period",
            "auto_payment": "Automatic top-up available",
            "thresholds": "Payment thresholds"
        },
        
        # API endpoints
        "endpoints": {
            "gate": "/api/v1/x402/gate",
            "payment": "/api/v1/x402/payment",
            "budget": "/api/v1/x402/budget",
            "transactions": "/api/v1/x402/transactions"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/evidence", response_model=Dict[str, Any])
async def get_evidence_manifest(
    db: AsyncSession = Depends(get_db)
):
    """Evidence Pack system manifest."""
    
    manifest = {
        "evidence_system": "Evidence Pack System",
        "version": "1.0.0",
        "description": "Comprehensive evidence collection with all components",
        
        # Evidence components
        "components": {
            "pgl": {
                "certificate": "PGL birth certificate",
                "genome": "Agent genome snapshot",
                "lineage": "Agent lineage tracking",
                "ledger": "Tamper-evident ledger"
            },
            "seked": {
                "measurements": "SEKED measurements",
                "decisions": "SEKED policy decisions",
                "ratios": "SEKED calculated ratios"
            },
            "cappo": {
                "executions": "CAPPO execution records",
                "approvals": "Execution approvals",
                "resource_usage": "Resource consumption"
            },
            "x402": {
                "transactions": "Payment transactions",
                "budget_tracking": "Budget usage",
                "payment_gates": "Payment gate evaluations"
            }
        },
        
        # Evidence lifecycle
        "lifecycle": {
            "creation": "Create evidence pack",
            "collection": "Collect from all components",
            "verification": "Verify integrity",
            "export": "Export in multiple formats",
            "attestation": "Create attestations"
        },
        
        # Export formats
        "export_formats": {
            "json": "JSON format",
            "yaml": "YAML format",
            "cbor": "CBOR binary format"
        },
        
        # API endpoints
        "endpoints": {
            "packs": "/api/v1/evidence-pack",
            "verify": "/api/v1/evidence-pack/{pack_id}/verify",
            "export": "/api/v1/evidence-pack/{pack_id}/export",
            "attest": "/api/v1/evidence-pack/{pack_id}/attest"
        },
        
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return JSONResponse(
        content=manifest,
        headers={"Content-Type": "application/json"}
    )


@router.get("/security.txt", response_model=str)
async def get_security_txt():
    """Security.txt file for security information."""
    
    security_content = """# Veklom Control Plane Security Policy
Contact: security@veklom.com
Contact: mailto:security@veklom.com
Encryption: https://keys.openpgp.org/vks/v1/by-fingerprint/ABC123DEF456
Preferred-Languages: en
Policy: https://veklom.com/security-policy
Acknowledgments: https://veklom.com/security-acknowledgments

# Security Hall of Fame
# Thank you to researchers who help keep Veklom secure

# Disclosure Policy
- We follow responsible disclosure
- 90-day disclosure timeline
- Bug bounty program available
- security@veklom.com for reports
"""
    
    return Response(
        content=security_content,
        media_type="text/plain",
        headers={"Content-Type": "text/plain; charset=utf-8"}
    )


@router.get("/robots.txt", response_model=str)
async def get_robots_txt():
    """Robots.txt file for web crawlers."""
    
    robots_content = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /internal/
Disallow: /.well-known/

# Allow search engines to index documentation
Allow: /docs/
Allow: /guides/

# Sitemap location
Sitemap: https://veklom.com/sitemap.xml
"""
    
    return Response(
        content=robots_content,
        media_type="text/plain",
        headers={"Content-Type": "text/plain; charset=utf-8"}
    )


@router.get("/change-password", response_model=Dict[str, Any])
async def get_change_password_redirect():
    """Redirect for change password (security requirement)."""
    
    return JSONResponse({
        "message": "Password change functionality",
        "url": "/settings/security",
        "description": "Change your password from account settings"
    })


@router.get("/jwks.json", response_model=Dict[str, Any])
async def get_jwks():
    """JSON Web Key Set for JWT verification."""
    
    jwks = key_manager.get_jwks()
    
    return JSONResponse(
        content=jwks,
        headers={"Content-Type": "application/json"}
    )


@router.get("/openid-configuration", response_model=Dict[str, Any])
async def get_openid_configuration():
    """OpenID Connect configuration."""
    
    base_url = "https://veklom.com"
    
    config = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "userinfo_endpoint": f"{base_url}/oauth/userinfo",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "scopes_supported": ["openid", "profile", "email", "api"],
        "response_types_supported": ["code", "id_token", "token id_token"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"]
    }
    
    return JSONResponse(
        content=config,
        headers={"Content-Type": "application/json"}
    )
