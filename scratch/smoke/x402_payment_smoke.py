import os
import uuid
from urllib.parse import urlparse

import httpx


BASE_URL = os.getenv("SMOKE_BASE_URL", "https://api.veklom.com").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "25"))
SMOKE_SECRET = os.getenv("SMOKE_TEST_SECRET", "").strip()
DEFAULT_API_HOST = (urlparse(BASE_URL).hostname or "").strip()
API_HOST_HEADER = os.getenv("SMOKE_API_HOST", DEFAULT_API_HOST).strip()


def main() -> int:
    passed = 0
    failed = 0
    failures: list[str] = []

    print("=================================================================")
    print("VEKLOM X402 PAYMENT SMOKE")
    print(f"BASE_URL={BASE_URL}")
    print(f"API_HOST_HEADER={API_HOST_HEADER or '<default-from-url>'}")
    print("=================================================================")

    unpaid_saw_402 = False

    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        base_headers = {"Host": API_HOST_HEADER} if API_HOST_HEADER else {}
        for idx in range(1, 8):
            response = client.post(
                f"{BASE_URL}/api/v1/ai/inference",
                headers=base_headers,
                json={"messages": [{"role": "user", "content": f"unpaid smoke {idx}"}]},
            )
            if response.status_code == 402:
                unpaid_saw_402 = True
                break

        if unpaid_saw_402:
            passed += 1
            print("[PASS] unpaid route flow reached payment-required 402")
        else:
            failed += 1
            failures.append(
                f"unpaid route flow did not produce 402 after repeated attempts (saw_402={unpaid_saw_402})"
            )
            print(f"[FAIL] unpaid route flow expected 402 (saw_402={unpaid_saw_402})")

        if not SMOKE_SECRET:
            failed += 1
            failures.append("SMOKE_TEST_SECRET env variable is required for paid/authenticated x402 check")
            print("[FAIL] missing SMOKE_TEST_SECRET for authenticated check")
            print("Set SMOKE_TEST_ENABLED=true on API and SMOKE_TEST_SECRET in CI/Coolify (not in repo).")
        else:
            token_headers = {"x-smoke-test-secret": SMOKE_SECRET}
            if API_HOST_HEADER:
                token_headers["Host"] = API_HOST_HEADER
            token_resp = client.post(
                f"{BASE_URL}/api/v1/smoke/eval-token",
                headers=token_headers,
                json={"fingerprint": f"ci-x402-smoke-{uuid.uuid4().hex[:8]}", "user_role": "admin"},
            )
            if token_resp.status_code != 200:
                failed += 1
                failures.append(f"POST /api/v1/smoke/eval-token status={token_resp.status_code}")
                print(f"[FAIL] POST /api/v1/smoke/eval-token -> {token_resp.status_code}")
            else:
                token = token_resp.json().get("access_token")
                if not token:
                    failed += 1
                    failures.append("POST /api/v1/smoke/eval-token missing access_token")
                    print("[FAIL] smoke token missing access_token")
                else:
                    paid_resp = client.post(
                        f"{BASE_URL}/api/v1/ai/inference",
                        headers={**base_headers, "Authorization": f"Bearer {token}"},
                        json={"messages": [{"role": "user", "content": "paid smoke"}]},
                    )
                    if paid_resp.status_code == 200:
                        passed += 1
                        print("[PASS] authenticated paid route -> 200")
                    else:
                        failed += 1
                        failures.append(f"authenticated /api/v1/ai/inference status={paid_resp.status_code}")
                        print(f"[FAIL] authenticated /api/v1/ai/inference -> {paid_resp.status_code}")

    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(f"- {item}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
