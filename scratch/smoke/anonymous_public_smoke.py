import json
import os
from typing import Iterable, Optional
from urllib.parse import urlparse

import httpx


BASE_URL = os.getenv("SMOKE_BASE_URL", "https://api.veklom.com").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "20"))
DEFAULT_API_HOST = (urlparse(BASE_URL).hostname or "").strip()
API_HOST_HEADER = os.getenv("SMOKE_API_HOST", DEFAULT_API_HOST).strip()


class SmokeRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def check(
        self,
        client: httpx.Client,
        name: str,
        method: str,
        path: str,
        expected: Iterable[int],
        json_required: bool = False,
        headers: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> None:
        url = f"{BASE_URL}{path}"
        request_headers = {}
        if API_HOST_HEADER:
            request_headers["Host"] = API_HOST_HEADER
        if headers:
            request_headers.update(headers)
        try:
            response = client.request(method, url, headers=request_headers, json=body)
            ok = response.status_code in set(expected)
            json_ok = True
            if json_required:
                try:
                    response.json()
                except Exception:
                    json_ok = False
            if ok and json_ok:
                self.passed += 1
                print(f"[PASS] {method} {path} -> {response.status_code}")
                return
            reason = f"status={response.status_code} expected={list(expected)}"
            if json_required and not json_ok:
                reason += " [non-JSON response]"
            self.failed += 1
            self.failures.append(f"{method} {path} {reason}")
            print(f"[FAIL] {method} {path} -> {reason}")
        except Exception as exc:
            self.failed += 1
            self.failures.append(f"{method} {path} exception={exc}")
            print(f"[FAIL] {method} {path} -> exception={exc}")

    def finish(self) -> int:
        print(f"PASS: {self.passed}")
        print(f"FAIL: {self.failed}")
        if self.failures:
            print("FAILURES:")
            for item in self.failures:
                print(f"- {item}")
        return 0 if self.failed == 0 else 1


def main() -> int:
    print("=================================================================")
    print("VEKLOM ANONYMOUS/PUBLIC SMOKE")
    print(f"BASE_URL={BASE_URL}")
    print(f"API_HOST_HEADER={API_HOST_HEADER or '<default-from-url>'}")
    print("=================================================================")

    runner = SmokeRunner()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        runner.check(client, "health", "GET", "/health", [200], json_required=True)
        runner.check(client, "health_v1", "GET", "/api/v1/health", [200], json_required=True)
        runner.check(client, "openapi", "GET", "/openapi.json", [200], json_required=True)
        runner.check(client, "docs", "GET", "/docs", [200])
        runner.check(client, "redoc", "GET", "/redoc", [200, 404])

        runner.check(client, "providers", "GET", "/api/v1/auth/providers", [200], json_required=True)
        runner.check(client, "auth_me_anon", "GET", "/api/v1/auth/me", [401], json_required=True)
        runner.check(
            client,
            "github_login",
            "GET",
            "/api/v1/auth/github/login",
            [200, 307],
            headers={"Accept": "application/json"},
        )
        runner.check(client, "eval_start", "POST", "/api/v1/evaluations/start", [200], json_required=True, body={})

        runner.check(client, "agent_json", "GET", "/.well-known/agent.json", [200], json_required=True)
        runner.check(client, "x402_json", "GET", "/.well-known/x402.json", [200], json_required=True)
        runner.check(client, "llms", "GET", "/llms.txt", [200])
        runner.check(client, "mcp_sse", "GET", "/mcp/sse", [200])
        runner.check(client, "pricing", "GET", "/api/v1/pricing", [200], json_required=True)

        runner.check(client, "workspace_page", "GET", "/workspace/", [200])
        runner.check(client, "terminal_page", "GET", "/terminal", [200])
        runner.check(client, "operator_center", "GET", "/operator-center/", [200, 401, 404])
        runner.check(client, "gpc_engine", "GET", "/gpc-engine/", [200, 403, 404])

        runner.check(client, "auth_gated_models", "GET", "/api/v1/models", [401, 403], json_required=True)
        runner.check(client, "auth_gated_pipelines", "GET", "/api/v1/pipelines", [401, 403], json_required=True)

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
