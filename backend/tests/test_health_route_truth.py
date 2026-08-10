from pathlib import Path


HEALTH_ROUTER = Path(__file__).parents[1] / "apps" / "api" / "routers" / "health.py"


def test_health_router_does_not_publish_fabricated_runtime_surfaces() -> None:
    source = HEALTH_ROUTER.read_text(encoding="utf-8")

    forbidden_routes = (
        '/api/quantum-metrics',
        '/api/uacp/hub/metrics',
        '/api/pgl/genome',
        '/api/pgl/ledger',
        '/api/cognitive/orchestrate',
    )
    for route in forbidden_routes:
        assert route not in source

    forbidden_claims = (
        '"lineage": "verified"',
        '"blocks": 14502',
        '"last_hash": "0x4f...9a"',
        '"determinism_ratio": 99.9',
        '"certainty_index": 0.98',
        '"fidelity": fidelity',
        '"Synthesizing optimal trajectory..."',
        '"Orchestration complete."',
    )
    for claim in forbidden_claims:
        assert claim not in source
