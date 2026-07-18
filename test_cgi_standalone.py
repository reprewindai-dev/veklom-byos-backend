import sys
from pprint import pprint

try:
    from backend.core.governance.cgi_evaluator import GeometryEvaluator, GeometryViolationException

    evaluator = GeometryEvaluator()

    # Valid pipeline plan
    valid_plan = {
        "agents": ["agent_1", "agent_2"],
        "tools": ["tool_A"],
        "parallel_branches": 1,
        "applied_policies": ["policy_1", "policy_2", "policy_3"],
        "verifiable_checkpoints": ["check_1", "check_2", "check_3"]
    }

    print("Testing Valid Plan:")
    result = evaluator.evaluate_geometry(valid_plan)
    pprint(result)

    # Invalid pipeline plan (too much autonomy, too little governance/evidence)
    invalid_plan = {
        "agents": ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5", "agent_6", "agent_7"],
        "tools": ["tool_A", "tool_B", "tool_C", "tool_D"],
        "parallel_branches": 5,
        "applied_policies": [],
        "verifiable_checkpoints": []
    }

    print("\nTesting Invalid Plan:")
    try:
        evaluator.evaluate_geometry(invalid_plan)
        print("FAILED: Should have raised GeometryViolationException")
    except GeometryViolationException as e:
        print(f"SUCCESS: Caught expected exception: {e.metrics['violations']}")
        pprint(e.metrics)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
