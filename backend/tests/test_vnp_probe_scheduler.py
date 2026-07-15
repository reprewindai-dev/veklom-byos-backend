import inspect

from backend.core.vnp import probes


def test_vnp_probe_runner_coordinates_replicas_with_postgres_advisory_lock():
    source = inspect.getsource(probes.run_vnp_probes)

    assert "pg_try_advisory_lock" in source
    assert "pg_advisory_unlock" in source
    assert probes.VNP_PROBE_ADVISORY_LOCK_ID > 0


def test_vnp_probe_cycle_timeout_allows_full_edge_swarm_roundtrip():
    assert probes.VNP_PROBE_CYCLE_TIMEOUT_SECONDS >= 60
