import os
import re
from urllib.parse import urlparse

import httpx


WEB_BASE_URL = os.getenv("SMOKE_WEB_BASE_URL", "https://veklom.com").rstrip("/")
WEB_HOST_HEADER = os.getenv("SMOKE_WEB_HOST", (urlparse(WEB_BASE_URL).hostname or "").strip())
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "30"))

PAGES = [
    "/",
    "/workspace/",
    "/terminal",
    "/gpc-engine/",
    "/command-center/",
]

EXPECTED_STATUS = {
    "/": {200},
    "/workspace/": {200},
    "/terminal": {200},
    "/gpc-engine/": {200, 403, 404},
    "/command-center/": {200, 401, 403, 404},
}

BAD_MARKERS = [
    "undefined",
    "nan",
]

BAD_PATTERNS = {
    "undefined": r"\bundefined\b",
    "nan": r"\bnan\b",
}

SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _visible_text(html_or_text: str) -> str:
    no_scripts = SCRIPT_STYLE_RE.sub(" ", html_or_text)
    no_tags = TAG_RE.sub(" ", no_scripts)
    return re.sub(r"\s+", " ", no_tags).strip()


def scan_text(path: str, text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for marker in BAD_MARKERS:
        pattern = BAD_PATTERNS[marker]
        if re.search(pattern, lowered):
            found.append(marker)
    return found


def run_http_checks() -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    failures: list[str] = []
    default_headers = {"Host": WEB_HOST_HEADER} if WEB_HOST_HEADER else {}
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for path in PAGES:
            url = f"{WEB_BASE_URL}{path}"
            try:
                response = client.get(url, headers=default_headers)
                expected = EXPECTED_STATUS.get(path, {200})
                if response.status_code not in expected:
                    failed += 1
                    failures.append(f"GET {path} status={response.status_code} expected={sorted(expected)}")
                    print(f"[FAIL] GET {path} -> {response.status_code}")
                    continue
                if response.status_code != 200:
                    passed += 1
                    print(f"[PASS] GET {path} -> {response.status_code}")
                    continue
                markers = scan_text(path, _visible_text(response.text))
                if markers:
                    failed += 1
                    failures.append(f"GET {path} placeholder markers found={markers}")
                    print(f"[FAIL] GET {path} -> markers={markers}")
                    continue
                passed += 1
                print(f"[PASS] GET {path} -> 200 clean")
            except Exception as exc:
                failed += 1
                failures.append(f"GET {path} exception={exc}")
                print(f"[FAIL] GET {path} -> exception={exc}")
    return passed, failed, failures


def run_playwright_checks() -> tuple[int, int, list[str]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("[INFO] playwright not available, falling back to HTTP checks")
        return run_http_checks()

    passed = 0
    failed = 0
    failures: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        for path in PAGES:
            url = f"{WEB_BASE_URL}{path}"
            try:
                response = page.goto(url, wait_until="networkidle", timeout=int(TIMEOUT * 1000))
                status = response.status if response else 0
                expected = EXPECTED_STATUS.get(path, {200})
                if status not in expected:
                    failed += 1
                    failures.append(f"GET {path} status={status} expected={sorted(expected)}")
                    print(f"[FAIL] GET {path} -> {status}")
                    continue
                if status != 200:
                    passed += 1
                    print(f"[PASS] GET {path} -> {status}")
                    continue
                body_text = page.locator("body").inner_text()
                markers = scan_text(path, body_text)
                if markers:
                    failed += 1
                    failures.append(f"GET {path} placeholder markers found={markers}")
                    print(f"[FAIL] GET {path} -> markers={markers}")
                    continue
                passed += 1
                print(f"[PASS] GET {path} -> 200 clean")
            except Exception as exc:
                failed += 1
                failures.append(f"GET {path} exception={exc}")
                print(f"[FAIL] GET {path} -> exception={exc}")
        browser.close()

    return passed, failed, failures


def main() -> int:
    print("=================================================================")
    print("VEKLOM UI/TELEMETRY SMOKE")
    print(f"WEB_BASE_URL={WEB_BASE_URL}")
    print(f"WEB_HOST_HEADER={WEB_HOST_HEADER or '<default-from-url>'}")
    print("=================================================================")
    passed, failed, failures = run_playwright_checks()
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(f"- {item}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
