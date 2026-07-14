from datetime import datetime, timedelta, timezone

from backend.apps.api.routers.vnp_beacon import CANONICAL_VNP_NODES, canonical_region, node_status


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


def test_reachable_hmac_node_without_ed25519_key_is_partial():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=0,
        latest_heartbeat=datetime.now(timezone.utc),
        observation_count=1,
    )

    assert status == "STANDBY"
    assert label == "Partially Implemented"


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


def test_keyed_node_requires_observation_before_connected():
    status, label = node_status(
        registration_status="registered",
        revocation_state=None,
        active_key_count=1,
        latest_heartbeat=datetime.now(timezone.utc),
        observation_count=0,
    )

    assert status == "STANDBY"
    assert label == "Partially Implemented"


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


def test_canonical_regions_use_physical_hetzner_location_codes():
    regions = {node["region"] for node in CANONICAL_VNP_NODES}

    assert regions == {
        "us-ashburn",
        "us-hillsboro",
        "de-nuremberg",
        "de-falkenstein",
        "sg-singapore",
    }
    assert all("-1" not in region and "-2" not in region for region in regions)


def test_legacy_cloud_region_aliases_normalize_to_physical_locations():
    assert canonical_region("us-east-1-ash") == "us-ashburn"
    assert canonical_region("us-west-1-hil") == "us-hillsboro"
    assert canonical_region("eu-central-1-nur") == "de-nuremberg"
    assert canonical_region("eu-central-1-fal") == "de-falkenstein"
    assert canonical_region("ap-southeast-1-sin") == "sg-singapore"
