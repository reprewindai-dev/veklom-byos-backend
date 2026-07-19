"""
Veklom Protocol Manifest
Serves the self-describing capability manifest and introspection endpoint.
"""
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Veklom Protocol"])

MANIFEST: Dict[str, Any] = {
    "protocolVersion": "1.0.0",
    "schemaReference": "https://api.veklom.com/openapi.json",
    "modules": ["inference", "pipeline", "identity", "evidence", "staking", "auth", "workspace", "payments"],
    "capabilities": {
        "deploy_infrastructure": {
            "convergenceGeometry": {
                "behaviorVectorDefinition": [
                    "deployment_latency_ms_p95",
                    "resource_allocation_accuracy",
                    "security_policy_compliance_score",
                    "minimum_agent_stability_index"
                ],
                "maxBehaviorDrift": 0.015,
                "builderFreedomBudget": {
                    "maxIndependentAgents": 3,
                    "maxParallelBranches": 2,
                    "allowableToolCombinations": 8
                },
                "governanceConstraints": {
                    "requiredSchemaDialect": "draft/2020-12",
                    "enforcedRbacPolicies": 5,
                    "statelessValidationRequired": True
                },
                "evidenceRequirements": {
                    "minTestSuites": 3,
                    "minDeterministicReplays": 5000,
                    "requiredProofTypes": [
                        "context_divergence_verification",
                        "policy_invariant_check"
                    ]
                }
            }
        },
        "inference_gateway": {
            "endpoint": "POST /api/v1/openai/v1/chat/completions",
            "description": "Governed OpenAI-compatible chat completions.",
            "accepts": ["Bearer JWT"],
            "models": ["qwen2.5-coder:1.5b", "gpt-4o-mini"]
        },
        "pipeline_compile": {
            "endpoint": "POST /api/v1/gpc/compile",
            "description": "Compile a governed pipeline graph into executable bytecode.",
            "accepts": ["Bearer JWT"]
        },
        "pipeline_execute": {
            "endpoint": "POST /api/v1/gpc/execute",
            "description": "Execute a compiled pipeline node or graph.",
            "accepts": ["Bearer JWT"]
        },
        "pgl_registry": {
            "endpoint": "GET /api/v1/pgl/registry",
            "description": "IdentityRAG cross-cluster tenant resolution mapping.",
            "accepts": ["Bearer JWT"]
        },
        "evidence_verify": {
            "endpoint": "POST /api/v1/evidence/verify",
            "description": "Verify cryptographic proof of an execution run.",
            "accepts": ["Bearer JWT"]
        },
        "vnp_stake": {
            "endpoint": "POST /api/v1/vnp/stake",
            "description": "Real-time SLA performance bonds.",
            "accepts": ["Bearer JWT"]
        },
        "auth_register": {
            "endpoint": "POST /api/v1/auth/register",
            "description": "Register a new tenant or user.",
            "accepts": []
        },
        "auth_login": {
            "endpoint": "POST /api/v1/auth/login",
            "description": "Authenticate a user.",
            "accepts": []
        },
        "workspace_overview": {
            "endpoint": "GET /api/v1/workspace/overview/live",
            "description": "Retrieve live workspace status.",
            "accepts": ["Bearer JWT"]
        },
        "agents_registry": {
            "endpoint": "GET /api/v1/agents",
            "description": "List governed agents.",
            "accepts": ["Bearer JWT"]
        },
        "x402_payments": {
            "endpoint": "POST /api/v1/x402",
            "description": "Settle proof of paid compute.",
            "accepts": ["Bearer JWT"]
        }
    },
    "links": {
        "self": "https://api.veklom.com/protocol.json",
        "cappo": "https://capi.veklom.com/protocol.json",
        "ledger": "https://ledger.veklom.com/protocol.json",
        "interlink": "https://interlink.veklom.com/protocol.json"
    }
}

class IntrospectQuery(BaseModel):
    query: str

@router.get("/protocol.json")
async def get_protocol_manifest():
    return MANIFEST

@router.post("/protocol/introspect")
async def introspect_protocol(query: IntrospectQuery):
    q = query.query.lower()
    matches = {}
    for cap_id, cap in MANIFEST.get("capabilities", {}).items():
        if q in cap_id.lower() or q in cap.get("description", "").lower() or q in cap.get("endpoint", "").lower():
            matches[cap_id] = cap
    return {"capabilities": matches}
