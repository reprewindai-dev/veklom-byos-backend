from pathlib import Path


MAIN = Path(__file__).parents[1] / "apps" / "api" / "main.py"


def test_startup_does_not_seed_or_sign_synthetic_vnp_evidence() -> None:
    source = MAIN.read_text(encoding="utf-8")

    forbidden = (
        "api_demo_veklom_1",
        "current_composite_score=99.9",
        'signature_value="local-node-signed"',
        'signature_alg="ed25519"',
        'worker_id="cappo-node-primary"',
        "p99_latency_ms=int(p95 * 1.1)",
        "trust_score=95.0",
    )

    for claim in forbidden:
        assert claim not in source
