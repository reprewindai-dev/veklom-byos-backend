"""
Veklom Backend Handshake
========================
Direct connection to veklom-byos-backend as the source of truth.
No Ollama. No LLM. Just raw backend verification.

What this does:
  1. Hits /health            — is the backend alive?
  2. Hits /status            — full system status
  3. Hits /api/v1/auth/login — gets a real JWT token
  4. Hits /api/v1/marketplace/vendors  — confirms DB is live
  5. Hits /api/v1/marketplace/models   — confirms model registry
  6. Hits /api/v1/irongrid/nodes       — confirms IronGrid
  7. Saves JWT to .env.agent           — agents use this automatically

Usage (PowerShell):
    cd C:\\Users\\antho\\Downloads\\pyo3-irongrid-api\\veklom-byos-backend
    python agents/handshake.py

Or with custom credentials:
    python agents/handshake.py --email you@email.com --password yourpass

After this runs successfully:
    All agents read VEKLOM_API_KEY from .env.agent automatically.
    Backend is confirmed live and ready.
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config — override via env or CLI args
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("VEKLOM_API_URL", "https://veklom.com").rstrip("/")
API_V1   = f"{BASE_URL}/api/v1"
TIMEOUT  = 15

# Colors for terminal output
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def info(msg): print(f"  {CYAN}→{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET}  {msg}")


# ---------------------------------------------------------------------------
# Handshake steps
# ---------------------------------------------------------------------------

async def check_health(client: httpx.AsyncClient) -> bool:
    """Step 1 — Raw health ping."""
    info(f"GET {BASE_URL}/health")
    try:
        r = await client.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if r.status_code == 200:
            ok(f"Backend alive — {r.json()}")
            return True
        else:
            fail(f"Health returned {r.status_code}: {r.text[:200]}")
            return False
    except httpx.ConnectError:
        fail(f"Cannot reach {BASE_URL} — Coolify port 8088 not forwarding or domain not resolving")
        return False
    except Exception as e:
        fail(f"Health check error: {e}")
        return False


async def check_status(client: httpx.AsyncClient) -> bool:
    """Step 2 — Full system status."""
    info(f"GET {BASE_URL}/status")
    try:
        r = await client.get(f"{BASE_URL}/status", timeout=TIMEOUT)
        if r.status_code == 200:
            ok(f"Status OK — {json.dumps(r.json())[:120]}")
            return True
        else:
            warn(f"Status returned {r.status_code} (non-critical)")
            return True  # non-fatal
    except Exception as e:
        warn(f"Status endpoint not available: {e} (non-critical)")
        return True  # non-fatal


async def login(client: httpx.AsyncClient, email: str, password: str) -> str | None:
    """Step 3 — Get real JWT from backend."""
    info(f"POST {API_V1}/auth/login")
    try:
        r = await client.post(
            f"{API_V1}/auth/login",
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token") or data.get("token")
            if token:
                ok(f"JWT obtained — {token[:40]}...")
                return token
            else:
                fail(f"Login succeeded but no token in response: {data}")
                return None
        elif r.status_code == 401:
            fail(f"Wrong credentials — check email/password")
            return None
        elif r.status_code == 500:
            fail(f"Backend 500 on login — database not connected. Check Coolify env vars.")
            return None
        else:
            fail(f"Login returned {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        fail(f"Login error: {e}")
        return None


async def check_authenticated(client: httpx.AsyncClient, token: str, path: str, label: str) -> bool:
    """Generic authenticated GET check."""
    info(f"GET {API_V1}{path}")
    try:
        r = await client.get(
            f"{API_V1}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            try:
                data = r.json()
                count = len(data) if isinstance(data, list) else "ok"
                ok(f"{label} — {count} record(s)")
            except Exception:
                ok(f"{label} — {r.text[:80]}")
            return True
        else:
            warn(f"{label} returned {r.status_code}: {r.text[:120]}")
            return False
    except Exception as e:
        fail(f"{label} error: {e}")
        return False


def save_token(token: str, email: str):
    """Save JWT to .env.agent so all agents load it automatically."""
    env_path = Path(".env.agent")
    lines = [
        f"# Auto-generated by agents/handshake.py",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        f"VEKLOM_API_URL={API_V1}",
        f"VEKLOM_API_KEY={token}",
        f"VEKLOM_AGENT_EMAIL={email}",
        f"OLLAMA_BASE_URL=http://localhost:11434",
        f"OLLAMA_MODEL=llama3",
        f"VEKLOM_AGENT_PROVIDER=ollama",
        f"AGENT_MAX_ITER=10",
        f"AGENT_DEBUG=0",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    ok(f"Saved to .env.agent — all agents will use this token automatically")


def load_env_agent():
    """Load .env.agent into os.environ if it exists."""
    env_path = Path(".env.agent")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------------------
# Main handshake
# ---------------------------------------------------------------------------

async def run_handshake(email: str, password: str):
    print()
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  VEKLOM BACKEND HANDSHAKE{RESET}")
    print(f"{BOLD}{CYAN}  Source of Truth: {BASE_URL}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print()

    passed = 0
    failed = 0

    async with httpx.AsyncClient() as client:

        # Step 1 — Health
        print(f"{BOLD}[1/6] Health Check{RESET}")
        if await check_health(client):
            passed += 1
        else:
            failed += 1
            print()
            print(f"{RED}{BOLD}FATAL: Backend unreachable. Fix Coolify port forwarding first.{RESET}")
            print(f"{YELLOW}  → Go to Coolify → your app → Network → set port 8088{RESET}")
            print()
            sys.exit(1)

        # Step 2 — Status
        print(f"\n{BOLD}[2/6] System Status{RESET}")
        await check_status(client)
        passed += 1

        # Step 3 — Login / JWT
        print(f"\n{BOLD}[3/6] Authentication (JWT){RESET}")
        token = await login(client, email, password)
        if token:
            passed += 1
        else:
            failed += 1
            print()
            warn("Continuing without JWT — authenticated endpoints will be skipped")
            print()

        if token:
            # Step 4 — Vendors
            print(f"\n{BOLD}[4/6] Marketplace Vendors{RESET}")
            if await check_authenticated(client, token, "/marketplace/vendors", "Vendors"):
                passed += 1
            else:
                failed += 1

            # Step 5 — Models
            print(f"\n{BOLD}[5/6] Marketplace Models{RESET}")
            if await check_authenticated(client, token, "/marketplace/models", "Models"):
                passed += 1
            else:
                failed += 1

            # Step 6 — IronGrid
            print(f"\n{BOLD}[6/6] IronGrid Nodes{RESET}")
            if await check_authenticated(client, token, "/irongrid/nodes", "IronGrid"):
                passed += 1
            else:
                failed += 1

            # Save token for all agents
            print(f"\n{BOLD}Saving credentials...{RESET}")
            save_token(token, email)
        else:
            warn("Skipping authenticated checks — no JWT")

    # Summary
    print()
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  HANDSHAKE RESULT: {GREEN}{passed} passed{RESET}{BOLD} / {RED}{failed} failed{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print()

    if failed == 0:
        print(f"{GREEN}{BOLD}  ✓ Backend fully operational. Agents are ready.{RESET}")
        print(f"{CYAN}  Run agents with:{RESET}")
        print(f"    python agents/agent_ollama.py")
        print(f"    python agents/agent_router.py")
    elif passed >= 3:
        print(f"{YELLOW}{BOLD}  ! Partial connection. Some endpoints need attention.{RESET}")
    else:
        print(f"{RED}{BOLD}  ✗ Backend not ready. Fix errors above first.{RESET}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_env_agent()

    parser = argparse.ArgumentParser(description="Veklom Backend Handshake")
    parser.add_argument("--email",    default=os.getenv("VEKLOM_AGENT_EMAIL", ""),    help="Login email")
    parser.add_argument("--password", default=os.getenv("VEKLOM_AGENT_PASSWORD", ""), help="Login password")
    parser.add_argument("--url",      default=os.getenv("VEKLOM_API_URL", ""),        help="Override backend URL")
    args = parser.parse_args()

    if args.url:
        BASE_URL = args.url.rstrip("/")
        API_V1   = f"{BASE_URL}/api/v1"

    if not args.email or not args.password:
        print(f"{YELLOW}No credentials provided. Running unauthenticated health check only.{RESET}")
        print(f"Usage: python agents/handshake.py --email you@email.com --password yourpass")
        print()
        args.email = ""
        args.password = ""

    asyncio.run(run_handshake(args.email, args.password))
