from datetime import datetime, timedelta, timezone

from backend.apps.api.routers.vnp_beacon import node_status


def test_registered_node_without_key_is_config_incomplete():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=0,
        latest_heartbeat=None,
        observation_count=0,
    )

    assert status == "STANDBY"
    assert label == "Config Incomplete"


def test_keyed_node_without_observations_is_partial():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=1,
        latest_heartbeat=datetime.now(timezone.utc),
        observation_count=0,
    )

    assert status == "STANDBY"
    assert label == "Partially Implemented"


def test_fresh_keyed_node_with_observation_is_connected():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=1,
        latest_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=10),
        observation_count=4,
    )

    assert status == "ATTESTING"
    assert label == "Connected"


def test_stale_heartbeat_is_disconnected():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=1,
        latest_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=301),
        observation_count=4,
    )

    assert status == "STANDBY"
    assert label == "Disconnected"
