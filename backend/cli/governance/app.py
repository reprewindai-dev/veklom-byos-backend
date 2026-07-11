import argparse
from backend.cli.governance.config import GovernanceCliConfig
from backend.cli.governance.context import build_context
from backend.cli.governance.output import render
from backend.cli.governance.checks import identity, rls, tiering, training, x402, dashboard, capi, incident


def main() -> int:
    parser = argparse.ArgumentParser(prog="veklom-governance")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check_sub = check.add_subparsers(dest="check_name", required=True)

    for name in ["all", "identity", "rls", "tiering", "training", "x402", "dashboard", "capi", "incident"]:
        p = check_sub.add_parser(name)
        p.add_argument("--tenant-id")
        p.add_argument("--model-family", default="default")
        p.add_argument("--db-url")
        p.add_argument("--redis-url")
        p.add_argument("--base-url", default="http://localhost:80")
        p.add_argument("--dashboard-url", default="http://localhost:3000")
        p.add_argument("--format", default="table", choices=["table", "json"])
        p.add_argument("--fail-fast", action="store_true")
        p.add_argument("--verbose", action="store_true")

    resolve = sub.add_parser("resolve-identity")
    resolve.add_argument("--agent-id")
    resolve.add_argument("--public-key")
    resolve.add_argument("--requester-provider-id", required=True)
    resolve.add_argument("--payment-proof", required=True)
    resolve.add_argument("--base-url", default="http://localhost:80")
    resolve.add_argument("--format", default="table", choices=["table", "json"])

    args = parser.parse_args()

    if args.command == "resolve-identity":
        import json, httpx
        payload = {"agent_id": args.agent_id, "public_key": args.public_key, "requester_provider_id": args.requester_provider_id}
        headers = {"X-Payment-Proof": args.payment_proof}
        with httpx.Client(base_url=args.base_url, timeout=20.0) as client:
            r = client.post("/api/v1/pgl/identity-rag/resolve", json=payload, headers=headers)
            print(json.dumps(r.json(), indent=2))
            return 0 if r.is_success else 1

    config = GovernanceCliConfig(
        db_url=args.db_url,
        redis_url=args.redis_url,
        base_url=args.base_url,
        dashboard_url=args.dashboard_url,
        tenant_id=args.tenant_id,
        model_family=args.model_family,
        output_format=args.format,
        fail_fast=args.fail_fast,
        verbose=args.verbose,
    )
    ctx = build_context(config)

    registry = {
        "identity": identity.run,
        "rls": rls.run,
        "tiering": tiering.run,
        "training": training.run,
        "x402": x402.run,
        "dashboard": dashboard.run,
        "capi": capi.run,
        "incident": incident.run,
    }

    selected = registry.keys() if args.check_name == "all" else [args.check_name]
    results = []
    for name in selected:
        result = registry[name](ctx)
        results.append(result)
        if config.fail_fast and not result.passed:
            break

    render(results, config.output_format)
    return 0 if all(r.passed for r in results) else 1
