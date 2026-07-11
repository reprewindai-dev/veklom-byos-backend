#!/usr/bin/env python3
"""Static route contract audit for the Veklom BYOS backend.

The CI workflow calls this script to catch accidental regressions in the
machine-facing API surface. It intentionally avoids importing the FastAPI app:
startup has database, Redis, telemetry, and background-worker side effects that
make a route audit brittle in CI.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
MAIN_APP = ROOT / "backend" / "apps" / "api" / "main.py"
ROUTER_DIR = ROOT / "backend" / "apps" / "api" / "routers"
INVENTORY = ROOT / "docs" / "BACKEND_ROUTE_INVENTORY.txt"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
INVENTORY_NOTE_LIMIT = 80

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
    """Read repository text files while tolerating a UTF-8 BOM."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def join_paths(*parts: str | None) -> str:
    """Join FastAPI mount, router prefix, and route path fragments."""
    path = ""
    for part in parts:
        if not part or part == "/":
            continue
        path = f"{path.rstrip('/')}/{part.lstrip('/')}"
    return path or "/"


def call_name(node: ast.AST) -> str:
    """Return a dotted-ish call name for the simple call patterns used here."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = call_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return ""


def literal_string(node: ast.AST | None) -> str | None:
    """Extract a literal string argument from an AST node, if present."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def literal_string_sequence(node: ast.AST | None) -> set[str]:
    """Extract literal strings from a static list, tuple, or set node."""
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set()
    return {value for element in node.elts if (value := literal_string(element))}


def parse_python(path: Path) -> ast.Module:
    """Parse a Python file for static route discovery without importing it."""
    try:
        return ast.parse(read_text(path), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"Cannot parse {path.relative_to(ROOT)}: {exc}") from exc


def router_prefix(source: str) -> str:
    """Find the `router = APIRouter(prefix=...)` prefix in router source."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Call) or call_name(node.value.func) != "APIRouter":
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "prefix":
                return literal_string(keyword.value) or ""
    return ""


def discover_router_mounts() -> list[tuple[str, str]]:
    """Discover `app.include_router(module.router, prefix=...)` mounts."""
    tree = parse_python(MAIN_APP)
    mounts: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or call_name(node.func) != "app.include_router":
            continue
        if not node.args:
            continue
        router_arg = node.args[0]
        if not (
            isinstance(router_arg, ast.Attribute)
            and router_arg.attr == "router"
            and isinstance(router_arg.value, ast.Name)
        ):
            continue
        prefix = ""
        for keyword in node.keywords:
            if keyword.arg == "prefix":
                prefix = literal_string(keyword.value) or ""
                break
        mounts.append((router_arg.value.id, prefix))
    return mounts


def api_route_methods(decorator: ast.Call) -> set[str]:
    """Collect static HTTP methods from `@router.api_route(..., methods=[...])`."""
    for keyword in decorator.keywords:
        if keyword.arg == "methods":
            return {
                method.upper()
                for method in literal_string_sequence(keyword.value)
                if method.lower() in HTTP_METHODS
            }
    return set()


def route_declarations(source: str) -> set[tuple[str, str]]:
    """Collect static `@router.<method>(...)` route declarations from source."""
    tree = ast.parse(source)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "router"):
                continue
            route_path = literal_string(decorator.args[0]) if decorator.args else None
            if not route_path or not route_path.startswith("/"):
                continue
            if func.attr.lower() in HTTP_METHODS:
                routes.add((func.attr.upper(), route_path))
            elif func.attr == "api_route":
                routes.update((method, route_path) for method in api_route_methods(decorator))
    return routes


def collect_source_routes(mounts: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    """Collect all live route contracts from mounted backend routers."""
    routes: set[tuple[str, str]] = set()

    for module, include_prefix in mounts:
        router_file = ROUTER_DIR / f"{module}.py"
        if not router_file.exists():
            continue

        source = read_text(router_file)
        base_prefix = router_prefix(source)

        for method, route_path in route_declarations(source):
            path = join_paths(include_prefix, base_prefix, route_path)
            routes.add((method, path))

    return routes


def collect_inventory_routes() -> set[tuple[str, str]]:
    """Read the documented route inventory when it exists."""
    if not INVENTORY.exists():
        return set()
    text = read_text(INVENTORY)
    return {(method, path) for method, path in INVENTORY_RE.findall(text)}


def print_routes(title: str, routes: Iterable[tuple[str, str, str]]) -> None:
    """Print required route failures with their contract reason."""
    print(title)
    for method, path, reason in routes:
        print(f"  - {method:<6} {path:<45} {reason}")


def print_route_pairs(title: str, routes: Iterable[tuple[str, str]]) -> None:
    """Print method/path route pairs in a stable order."""
    print(title)
    route_list = sorted(routes)
    for method, path in route_list[:INVENTORY_NOTE_LIMIT]:
        print(f"  - {method:<6} {path}")
    hidden = len(route_list) - INVENTORY_NOTE_LIMIT
    if hidden > 0:
        print(f"  ... {hidden} more live routes are absent from the inventory.")


def main() -> int:
    """Run the backend route contract audit."""
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

    stale_inventory = sorted(source_routes - inventory_routes) if inventory_routes else []

    print("Route contract audit passed.")
    print(f"  Router mounts parsed: {len(mounts)}")
    print(f"  Source routes parsed: {len(source_routes)}")
    if inventory_routes:
        print(f"  Inventory routes parsed: {len(inventory_routes)}")
    if stale_inventory:
        print_route_pairs(
            "\nNon-failing note: docs/BACKEND_ROUTE_INVENTORY.txt is missing these live source routes:",
            stale_inventory,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
