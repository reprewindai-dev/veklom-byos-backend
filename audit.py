#!/usr/bin/env python3
"""Static route contract audit for the Veklom BYOS backend.

The CI workflow calls this script to catch accidental regressions in the
machine-facing API surface. It intentionally avoids importing the FastAPI app:
startup has database, Redis, telemetry, and background-worker side effects that
make a route audit brittle in CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
MAIN_APP = ROOT / "backend" / "apps" / "api" / "main.py"
ROUTER_DIR = ROOT / "backend" / "apps" / "api" / "routers"
INVENTORY = ROOT / "docs" / "BACKEND_ROUTE_INVENTORY.txt"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

INCLUDE_RE = re.compile(
    r"app\.include_router\(\s*"
    r"(?P<module>[A-Za-z_][A-Za-z0-9_]*)\.router"
    r"(?:\s*,\s*prefix\s*=\s*[\"'](?P<prefix>[^\"']*)[\"'])?",
    re.MULTILINE,
)
ROUTER_PREFIX_RE = re.compile(
    r"router\s*=\s*APIRouter\s*\("
    r"(?P<body>.{0,1200}?)"
    r"(?:\n\s*\)|\))",
    re.DOTALL,
)
PREFIX_ARG_RE = re.compile(r"prefix\s*=\s*[\"'](?P<prefix>[^\"']*)[\"']")
ROUTE_RE = re.compile(
    r"@router\.(?P<method>get|post|put|patch|delete|head|options)"
    r"\(\s*[\"'](?P<path>/[^\"']*)[\"']",
    re.IGNORECASE,
)
INVENTORY_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S+)", re.MULTILINE)


REQUIRED_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/health", "public health check"),
    ("GET", "/.well-known/agent.json", "agent manifest discovery"),
    ("GET", "/.well-known/x402.json", "x402 payment discovery"),
    ("GET", "/llms.txt", "LLM crawler positioning"),
    ("GET", "/api/v1/pricing", "machine-readable pricing"),
    ("POST", "/api/v1/auth/login", "email/password login"),
    ("POST", "/api/v1/auth/register", "workspace registration"),
    ("POST", "/api/v1/auth/eval-session", "public eval session bootstrap"),
    ("GET", "/api/v1/ai/models", "model catalog"),
    ("POST", "/api/v1/ai/complete", "completion execution"),
    ("POST", "/api/v1/ai/inference", "paid inference execution"),
    ("POST", "/api/v1/ai/chat", "chat execution"),
    ("POST", "/api/v1/gpc/intent-to-plan", "governed plan compilation"),
    ("POST", "/api/v1/gpc/runs", "governed plan execution"),
    ("GET", "/api/v1/pipelines", "pipeline listing"),
    ("POST", "/api/v1/pipelines", "pipeline creation"),
    ("POST", "/api/v1/pipelines/{pipeline_id}/run", "pipeline trigger"),
    ("POST", "/api/v1/evidence/verify", "evidence verification"),
    ("GET", "/api/v1/evidence/packs", "evidence pack listing"),
    ("GET", "/api/v1/compliance/report", "compliance report"),
    ("POST", "/api/v1/compliance/report", "compliance report generation"),
    ("GET", "/api/v1/x402/config", "x402 runtime config"),
    ("POST", "/api/v1/x402/verify", "x402 proof verification"),
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def join_paths(*parts: str | None) -> str:
    path = ""
    for part in parts:
        if not part or part == "/":
            continue
        path = f"{path.rstrip('/')}/{part.lstrip('/')}"
    return path or "/"


def router_prefix(source: str) -> str:
    match = ROUTER_PREFIX_RE.search(source)
    if not match:
        return ""
    prefix = PREFIX_ARG_RE.search(match.group("body"))
    return prefix.group("prefix") if prefix else ""


def discover_router_mounts() -> list[tuple[str, str]]:
    source = read_text(MAIN_APP)
    mounts: list[tuple[str, str]] = []
    for match in INCLUDE_RE.finditer(source):
        module = match.group("module")
        prefix = match.group("prefix") or ""
        mounts.append((module, prefix))
    return mounts


def collect_source_routes(mounts: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()

    for module, include_prefix in mounts:
        router_file = ROUTER_DIR / f"{module}.py"
        if not router_file.exists():
            continue

        source = read_text(router_file)
        base_prefix = router_prefix(source)

        for route in ROUTE_RE.finditer(source):
            method = route.group("method").upper()
            if method.lower() not in HTTP_METHODS:
                continue
            path = join_paths(include_prefix, base_prefix, route.group("path"))
            routes.add((method, path))

    return routes


def collect_inventory_routes() -> set[tuple[str, str]]:
    if not INVENTORY.exists():
        return set()
    text = read_text(INVENTORY)
    return {(method, path) for method, path in INVENTORY_RE.findall(text)}


def print_routes(title: str, routes: Iterable[tuple[str, str, str]]) -> None:
    print(title)
    for method, path, reason in routes:
        print(f"  - {method:<6} {path:<45} {reason}")


def main() -> int:
    if not MAIN_APP.exists():
        print(f"Route audit failed: missing {MAIN_APP.relative_to(ROOT)}")
        return 1

    mounts = discover_router_mounts()
    source_routes = collect_source_routes(mounts)
    inventory_routes = collect_inventory_routes()

    if len(source_routes) < 250:
        print(
            "Route audit failed: parsed too few source routes "
            f"({len(source_routes)}). Check audit.py router parsing."
        )
        return 1

    missing = [
        (method, path, reason)
        for method, path, reason in REQUIRED_ROUTES
        if (method, path) not in source_routes
    ]
    if missing:
        print_routes("Route audit failed: required route contracts are missing:", missing)
        print(f"\nParsed {len(source_routes)} source routes from {len(mounts)} router mounts.")
        return 1

    stale_inventory = [
        (method, path, reason)
        for method, path, reason in REQUIRED_ROUTES
        if inventory_routes and (method, path) not in inventory_routes
    ]

    print("Route contract audit passed.")
    print(f"  Router mounts parsed: {len(mounts)}")
    print(f"  Source routes parsed: {len(source_routes)}")
    if inventory_routes:
        print(f"  Inventory routes parsed: {len(inventory_routes)}")
    if stale_inventory:
        print("\nNon-failing note: docs/BACKEND_ROUTE_INVENTORY.txt is missing these live routes:")
        for method, path, _ in stale_inventory:
            print(f"  - {method:<6} {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
