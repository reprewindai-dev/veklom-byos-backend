import json
from backend.core.governance.checker_types import CheckResult


def render(results: list[CheckResult], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps([r.__dict__ for r in results], indent=2, default=str))
        return

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.summary}")
        if result.details:
            for k, v in result.details.items():
                print(f"    - {k}: {v}")
