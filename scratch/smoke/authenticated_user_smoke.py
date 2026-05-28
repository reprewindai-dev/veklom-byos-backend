import os
from typing import Iterable, Optional

import httpx


BASE_URL = os.getenv("SMOKE_BASE_URL", "https://api.veklom.com").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "25"))
SMOKE_SECRET = os.getenv("SMOKE_TEST_SECRET", "").strip()


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
        try:
            response = client.request(method, url, headers=headers, json=body)
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
    print("=================================================================")

    runner = SmokeRunner()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        if not SMOKE_SECRET:
            runner.failed += 1
            runner.failures.append("SMOKE_TEST_SECRET env variable is required for /api/v1/smoke/eval-token")
            print("[FAIL] Missing SMOKE_TEST_SECRET environment variable")
            return runner.finish()

        token_resp = client.post(
            f"{BASE_URL}/api/v1/smoke/eval-token",
            headers={"x-smoke-test-secret": SMOKE_SECRET},
            json={"fingerprint": "ci-auth-smoke", "user_role": "admin"},
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
        runner.check(client, "GET", "/api/v1/workspace/status/data", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/workspace/models", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/ai/models", [200], headers=auth_headers)
        runner.check(client, "GET", "/api/v1/marketplace/agents", [200], headers=auth_headers)
        runner.check(
            client,
            "POST",
            "/api/v1/ai/inference",
            [200],
            headers=auth_headers,
            body={"messages": [{"role": "user", "content": "smoke test"}]},
        )

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())

