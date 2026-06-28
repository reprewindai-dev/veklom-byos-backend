import re
import sys

with open("backend/apps/api/routers/capi.py", "r") as f:
    content = f.read()

# We need to replace the return and exception throwing at the end of governed_execution_intercept

# 1. Replace the HTTPException raising at line 583 (the HARD VETO)
hard_veto_pattern = r"raise HTTPException\(\s*status_code=status_code,\s*detail=\{(.*?)\}\s*\)"
# We don't want to break the syntax. Let's just find the big if not is_approved block:
block_match = re.search(r"(if not is_approved:.*?)# Phase 6: Forward to Execution Sandbox", content, re.DOTALL)
if block_match:
    original_block = block_match.group(1)
    
    # We will just change the `raise HTTPException` to setting an exception variable
    new_block = original_block.replace("raise HTTPException(", "veto_exception = HTTPException(")
    content = content.replace(original_block, "veto_exception = None\n    " + new_block)
else:
    print("Could not find hard veto block")
    sys.exit(1)

# 2. Replace the return ExecutionReceipt(...) at the bottom
return_pattern = r"(return ExecutionReceipt\((.*?)\))"
return_match = re.search(return_pattern, content, re.DOTALL)
if return_match:
    original_return = return_match.group(1)
    
    new_return = """
    receipt_data = {
        "status": "EXECUTED",
        "intent_hash": intent_hash,
        "verdict": "APPROVED_BY_cAPI",
        "evidence_chain_id": evidence_chain_id,
        "result": execution_result,
        "trust_delta": trust_delta,
        "new_trust_score": new_trust_score,
        "risk_score": risk_score
    }
    """
    content = content.replace(original_return, new_return)
else:
    print("Could not find return statement")
    sys.exit(1)

# 3. Add the event generator and streaming response at the very end of the function
# We can just append it before the quarantine resolution endpoints
quarantine_marker = "# =====================================================================\n# QUARANTINE RESOLUTION ENDPOINTS"
if quarantine_marker in content:
    generator_code = """
    async def event_generator():
        phases = [
            (1, "Identity & Cryptography Gate"),
            (2, "Three-Tier Policy Composition Gate"),
            (3, "Safety & Anomaly Gate"),
            (4, "Budget & Spend Gate"),
            (5, "Approval Gate"),
            (6, "Execution Sandbox"),
            (7, "Evidence Sealing"),
            (8, "Audit Logging"),
            (9, "Response Egress")
        ]
        
        for phase_num, desc in phases:
            if str(phase_num) in phase_results and phase_results[str(phase_num)] != "PENDING":
                status_text = phase_results[str(phase_num)]
                msg = f"Phase {phase_num} ({desc}): {status_text}"
                yield f"data: {json.dumps({'type': 'log', 'phase': phase_num, 'text': msg})}\\n\\n"
                await asyncio.sleep(0.15)
                
                if "FAILED" in status_text:
                    break
                    
        if veto_exception:
            yield f"data: {json.dumps({'type': 'error', 'detail': veto_exception.detail})}\\n\\n"
            # Fastapi doesn't allow raising exception in streaming response to change HTTP status easily,
            # but the frontend will see the error object.
        else:
            yield f"data: {json.dumps({'type': 'receipt', 'data': receipt_data})}\\n\\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

"""
    content = content.replace(quarantine_marker, generator_code + quarantine_marker)

with open("backend/apps/api/routers/capi.py", "w") as f:
    f.write(content)

print("capi.py patched successfully")
