from backend.core.security.middlewares import _is_zero_trust_public_path


def test_benchmark_card_reads_are_public_for_frontend_scorecards():
    assert _is_zero_trust_public_path("/api/v1/benchmarks/card/did:veklom:guard")
    assert _is_zero_trust_public_path("/api/benchmarks/card/did:veklom:guard")


def test_benchmark_mutations_stay_protected():
    assert not _is_zero_trust_public_path("/api/v1/benchmarks/staking/markets/m1/stake", "POST")
    assert not _is_zero_trust_public_path("/api/benchmarks/staking/markets/m1/stake", "POST")
