from pathlib import Path


HEALTH = Path(__file__).parents[1] / "apps" / "api" / "routers" / "health.py"


def test_health_router_does_not_publish_fabricated_governance_state() -> None:
    source = HEALTH.read_text(encoding="utf-8")

    forbidden = (
        "/api/quantum-metrics",
        "/api/uacp/hub/metrics",
        "/api/agents/task-force",
        "/api/pgl/genome",
        "/api/pgl/ledger",
        "/api/cognitive/orchestrate",
        "fidelity = 99.99",
        '"leakage_rate": 0.001',
        '"determinism_ratio": 99.9',
        '"certainty_index": 0.98',
        '"lineage": "verified"',
        '"blocks": 14502',
        '"last_hash": "0x4f...9a"',
        '"Orchestration complete."',
    )

    for claim in forbidden:
        assert claim not in source


def test_shallow_health_keeps_explicit_verification_boundary() -> None:
    source = HEALTH.read_text(encoding="utf-8")

    assert '"verification_scope": "PROCESS_ONLY"' in source
    assert '"dependencies": "NOT_VERIFIED"' in source
