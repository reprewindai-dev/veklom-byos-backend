from backend.core.middleware.x402 import _is_free_route


def test_public_vnp_benchmark_card_routes_are_free():
    assert _is_free_route("/api/v1/benchmarks/card/did:veklom:guard")
    assert _is_free_route("/api/benchmarks/card/did:veklom:guard")


def test_paid_benchmark_routes_are_not_accidentally_freed():
    assert not _is_free_route("/api/v1/benchmarks/staking/markets")
    assert not _is_free_route("/api/v1/benchmarks/staking/stake")
