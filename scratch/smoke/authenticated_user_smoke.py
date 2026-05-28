import os
import uuid
from typing import Iterable, Optional
from urllib.parse import urlparse

import httpx


BASE_URL = os.getenv("SMOKE_BASE_URL", "https://api.veklom.com").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "25"))
SMOKE_SECRET = os.getenv("SMOKE_TEST_SECRET", "").strip()
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
        method: str,
        path: str,
        expected: Iterable[int],
        headers: Optional[dict] = None,
        body: Optional[dict] = None,
        json_required: bool = True,
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
    print("VEKLOM AUTHENTICATED USER SMOKE")
    print(f"BASE_URL={BASE_URL}")
    print(f"API_HOST_HEADER={API_HOST_HEADER or '<default-from-url>'}")
    print("=================================================================")

    runner = SmokeRunner()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        if not SMOKE_SECRET:
            runner.failed += 1
            runner.failures.append("SMOKE_TEST_SECRET env variable is required for /api/v1/smoke/eval-token")
            print("[FAIL] Missing SMOKE_TEST_SECRET environment variable.")
            print("Set SMOKE_TEST_ENABLED=true on API and SMOKE_TEST_SECRET in CI/Coolify (not in repo).")
            return runner.finish()

        token_headers = {"x-smoke-test-secret": SMOKE_SECRET}
        if API_HOST_HEADER:
            token_headers["Host"] = API_HOST_HEADER
        token_resp = client.post(
            f"{BASE_URL}/api/v1/smoke/eval-token",
            headers=token_headers,
            json={"fingerprint": f"ci-auth-smoke-{uuid.uuid4().hex[:8]}", "user_role": "admin"},
        )
        if token_resp.status_code != 200:
            runner.failed += 1
            runner.failures.append(
                f"POST /api/v1/smoke/eval-token status={token_resp.status_code} body={token_resp.text[:200]}"
            )
            print(f"[FAIL] POST /api/v1/smoke/eval-token -> {token_resp.status_code}")
            return runner.finish()

        token_payload = token_resp.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            runner.failed += 1
            runner.failures.append("POST /api/v1/smoke/eval-token missing access_token")
            print("[FAIL] POST /api/v1/smoke/eval-token -> missing access_token")
            return runner.finish()

        runner.passed += 1
        print("[PASS] POST /api/v1/smoke/eval-token -> 200")

        auth_headers = {"Authorization": f"Bearer {access_token}"}
        runner.check(client, "GET", "/api/v1/auth/me", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/users/me", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/models", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/pipelines", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/marketplace/agents", [200], headers=auth_headers)

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
