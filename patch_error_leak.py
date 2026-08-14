import re

with open("backend/core/services/pgl_identity_gate.py", "r") as f:
    content = f.read()

content = content.replace(
"""        except Exception as _lc_exc:
            # Lifecycle module failure MUST be fatal to prevent unauthorized execution.
            logger.error(f"[PGLGate] Lifecycle check failed for '{actor_id}': {_lc_exc}")
            raise PGLIdentityError(
                actor_id=actor_id,
                reason=f"Failed to evaluate identity lifecycle: {_lc_exc}"
            ) from _lc_exc""",
"""        except Exception as _lc_exc:
            # Lifecycle module failure MUST be fatal to prevent unauthorized execution.
            logger.error(f"[PGLGate] Lifecycle check failed for '{actor_id}': {_lc_exc}")
            raise PGLIdentityError(
                actor_id=actor_id,
                reason="Identity lifecycle evaluation unavailable"
            ) from _lc_exc"""
)

with open("backend/core/services/pgl_identity_gate.py", "w") as f:
    f.write(content)

with open("backend/tests/test_pgl_identity_gate.py", "r") as f:
    test_content = f.read()

test_content = test_content.replace(
"""    assert "Failed to evaluate identity lifecycle: Simulated DB failure" in exc_info.value.reason""",
"""    # Assert the internal error is NOT leaked to the caller
    assert "Simulated DB failure" not in exc_info.value.reason
    assert "Identity lifecycle evaluation unavailable" in exc_info.value.reason"""
)

with open("backend/tests/test_pgl_identity_gate.py", "w") as f:
    f.write(test_content)

with open("backend/tests/test_pgl_identity_gate.py", "r") as f:
    content = f.read()

# We need to assert that commit_intent is not called on failure path.
# Since the method raises early, we can check if it raises early. Wait, the test already checks it raises PGLIdentityError.
# But we can explicitly patch pgl.commit_intent and assert it's not called.

# Let's modify the test function test_require_lifecycle_failure_raises_exception to include the patch

import sys
sys.exit(0)
