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
            "models": ["qwen2.5-coder:1.5b", "gpt-4o-mini"],
            "status": "AVAILABLE",
            "required_scopes": ["inference:execute"],
            "side_effect_class": "COMPUTE",
            "requires_approval": False,
            "input_schema_ref": "#/components/schemas/ChatCompletionRequest"
        },
        "pipeline_compile": {
            "endpoint": "POST /api/v1/gpc/compile",
            "description": "Compile a governed pipeline graph into executable bytecode.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["gpc:compile"],
            "side_effect_class": "COMPUTE",
            "requires_approval": False,
            "input_schema_ref": "#/components/schemas/PipelineCompilationRequest"
        },
        "pipeline_execute": {
            "endpoint": "POST /api/v1/gpc/execute",
            "description": "Execute a compiled pipeline node or graph.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["gpc:execute"],
            "side_effect_class": "STATE_MUTATION",
            "requires_approval": True,
            "input_schema_ref": "#/components/schemas/PipelineExecutionRequest"
        },
        "pgl_registry": {
            "endpoint": "GET /api/v1/pgl/registry",
            "description": "IdentityRAG cross-cluster tenant resolution mapping.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["pgl:read"],
            "side_effect_class": "READ_ONLY",
            "requires_approval": False,
            "input_schema_ref": ""
        },
        "evidence_verify": {
            "endpoint": "POST /api/v1/evidence/verify",
            "description": "Verify cryptographic proof of an execution run.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["evidence:verify"],
            "side_effect_class": "COMPUTE",
            "requires_approval": False,
            "input_schema_ref": "#/components/schemas/EvidenceVerificationRequest"
        },
        "vnp_stake": {
            "endpoint": "POST /api/v1/vnp/stake",
            "description": "Real-time SLA performance bonds.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["vnp:stake"],
            "side_effect_class": "FINANCIAL",
            "requires_approval": True,
            "input_schema_ref": "#/components/schemas/VnpStakeRequest"
        },
        "auth_register": {
            "endpoint": "POST /api/v1/auth/register",
            "description": "Register a new tenant or user.",
            "accepts": [],
            "status": "AVAILABLE",
            "required_scopes": [],
            "side_effect_class": "STATE_MUTATION",
            "requires_approval": False,
            "input_schema_ref": "#/components/schemas/UserCreate"
        },
        "auth_login": {
            "endpoint": "POST /api/v1/auth/login",
            "description": "Authenticate a user.",
            "accepts": [],
            "status": "AVAILABLE",
            "required_scopes": [],
            "side_effect_class": "READ_ONLY",
            "requires_approval": False,
            "input_schema_ref": "#/components/schemas/LoginRequest"
        },
        "workspace_overview": {
            "endpoint": "GET /api/v1/workspace/overview/live",
            "description": "Retrieve live workspace status.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["workspace:read"],
            "side_effect_class": "READ_ONLY",
            "requires_approval": False,
            "input_schema_ref": ""
        },
        "agents_registry": {
            "endpoint": "GET /api/v1/agents",
            "description": "List governed agents.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["agents:read"],
            "side_effect_class": "READ_ONLY",
            "requires_approval": False,
            "input_schema_ref": ""
        },
        "x402_payments": {
            "endpoint": "POST /api/v1/x402",
            "description": "Settle proof of paid compute.",
            "accepts": ["Bearer JWT"],
            "status": "AVAILABLE",
            "required_scopes": ["x402:settle"],
            "side_effect_class": "FINANCIAL",
            "requires_approval": True,
            "input_schema_ref": "#/components/schemas/PaymentSettlementRequest"
        }
    },
    "links": {
        "self": "https://api.veklom.com/protocol.json",
        "cappo": "https://capi.veklom.com/protocol.json",
        "ledger": "https://ledger.veklom.com/protocol.json",
        "interlink": "https://interlink.veklom.com/protocol.json"
    }
}

from typing import Optional, List

class IntrospectQuery(BaseModel):
    query: str
    intent: Optional[str] = None
    required_inputs: Optional[List[str]] = None
    required_output: Optional[str] = None
    side_effect_level: Optional[str] = None
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None

class CapabilityMatch(BaseModel):
    capability_id: str
    match_score: float
    status: str
    endpoint: str
    required_scopes: List[str]
    side_effect_class: str
    requires_approval: bool
    schema_ref: str
    health_verified_at: str

@router.get("/protocol.json")
async def get_protocol_manifest():
    return MANIFEST

@router.post("/protocol/introspect")
async def introspect_protocol(query: IntrospectQuery):
    # Semantic token matching
    search_str = query.intent if query.intent else query.query
    tokens = set(search_str.lower().split())
    
    matches_list = []
    matches_dict = {}
    for cap_id, cap in MANIFEST.get("capabilities", {}).items():
        cap_desc = cap.get("description", "").lower()
        cap_tokens = set(cap_desc.split() + cap_id.replace("_", " ").split())
        
        # Jaccard similarity for token match score
        intersection = tokens.intersection(cap_tokens)
        union = tokens.union(cap_tokens)
        score = len(intersection) / len(union) if union else 0.0
        
        # Also do a naive substring match as fallback
        if score > 0.05 or search_str.lower() in cap_id.lower() or search_str.lower() in cap_desc:
            matches_dict[cap_id] = cap
            matches_list.append(CapabilityMatch(
                capability_id=cap_id,
                match_score=round(max(score, 1.0 if search_str.lower() in cap_id.lower() else 0.5), 2),
                status=cap.get("status", "AVAILABLE"),
                endpoint=cap.get("endpoint", "UNKNOWN"),
                required_scopes=cap.get("required_scopes", []),
                side_effect_class=cap.get("side_effect_class", "COMPUTE"),
                requires_approval=cap.get("requires_approval", False),
                schema_ref=cap.get("input_schema_ref", ""),
                health_verified_at="2026-07-19T00:00:00Z"
            ))
            
    # Sort by match score descending
    matches_list.sort(key=lambda x: x.match_score, reverse=True)
    
    # Return both formats to prevent breaking clients
    return {
        "capabilities": matches_dict,
        "matches": [m.model_dump() for m in matches_list]
    }
