import asyncio
import json
import uuid
from typing import Dict, Any

# Mocking parts for isolated test
class MockUser:
    def __init__(self):
        self.id = "actor-123"
        self.workspace_id = "workspace-abc"

async def test_vnp_v2_logic():
    print("Testing VNP v2.0 Logic Alignment...")

    from backend.core.vnp.models import InvocationRequest, CapabilityContext, TransportType, RiskLevel
    from backend.core.vnp.enforcer import SafetyEnforcer, PolicyEngine, PolicyDecision

    # Setup Request
    ctx = CapabilityContext(
        tenant_id="workspace-abc",
        actor_id="actor-123",
        transport=TransportType.Http,
        trace_id=str(uuid.uuid4()),
        environment="prod",
        is_untrusted_content=False,
        enabled_toolsets=["github"]
    )

    req = InvocationRequest(
        capability_id="github.get_repo",
        arguments={"owner": "veklom", "repo": "interlink-rs"},
        context=ctx
    )

    # Test Enforcer
    from backend.apps.api.routers.vnp_v2 import MOCK_CAPABILITIES
    enforcer = SafetyEnforcer(MOCK_CAPABILITIES)

    cap, error = enforcer.validate_invocation(req)
    if error:
        print(f"✗ Safety Enforcer failed: {error}")
    else:
        print(f"✓ Safety Enforcer passed for {cap.id}")

    # Test Policy Engine
    decision = PolicyEngine.evaluate(req, cap)
    print(f"✓ Policy Engine decision: {decision.decision}")

    # Test Sanitization
    dirty_result = {"name": "repo", "token": "SENSITIVE_DATA", "nested": {"password": "123"}}
    clean_result = enforcer.sanitize_output(dirty_result)
    if clean_result["token"] == "[REDACTED]" and clean_result["nested"]["password"] == "[REDACTED]":
        print("✓ Output Sanitization working correctly.")
    else:
        print(f"✗ Output Sanitization failed: {clean_result}")

    # Test High Risk + Prod (Should Require Approval)
    req_high = InvocationRequest(
        capability_id="github.create_issue", # Medium risk
        arguments={"owner": "veklom", "repo": "interlink-rs", "title": "Test"},
        context=ctx
    )
    cap_high = [c for c in MOCK_CAPABILITIES if c.id == "github.create_issue"][0]

    # Manually change risk to High for test
    cap_high.risk = RiskLevel.High
    decision_high = PolicyEngine.evaluate(req_high, cap_high)
    if decision_high.decision == "RequireApproval":
        print("✓ Environment-aware policy (High risk in prod) correctly requires approval.")
    else:
        print(f"✗ High risk policy failed: {decision_high.decision}")

    print("VNP v2.0 Logic Alignment Verification Complete.")

if __name__ == "__main__":
    asyncio.run(test_vnp_v2_logic())
