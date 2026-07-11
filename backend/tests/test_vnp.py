import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import nacl.signing
import pytest
from fastapi.testclient import TestClient
from nacl.encoding import HexEncoder

from backend.apps.api.main import app
from backend.db.models.vnp import Validator

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    with patch("backend.apps.api.routers.vnp.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        yield mock_db


def test_vnp_ingestion_invalid_validator():
    """Test ingestion fails if validator does not exist."""
    payload = {
        "api_id": "api-openai-com",
        "validator_id": "invalid-val",
        "region": "us-east-1",
        "latency_ms": 150,
        "http_status_code": 200,
        "success": True,
    }

    # We need to mock the database get directly inside the route
    with patch(
        "backend.apps.api.routers.vnp.AsyncSession.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None

        response = client.post(
            "/api/v1/vnp/ingestion",
            json=payload,
            headers={"X-VNP-Signature": "fakesig"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or inactive validator"


def test_vnp_ingestion_invalid_signature():
    """Test ingestion fails if the signature is invalid."""
    signing_key = nacl.signing.SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")

    mock_validator = Validator(
        id=uuid.uuid4(), name="Node1", public_key=public_key_hex, status="active"
    )

    payload = {
        "api_id": "api-openai-com",
        "validator_id": "valid-val",
        "region": "us-east-1",
        "latency_ms": 150,
        "http_status_code": 200,
        "success": True,
    }

    with patch(
        "backend.apps.api.routers.vnp.AsyncSession.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_validator

        response = client.post(
            "/api/v1/vnp/ingestion",
            json=payload,
            headers={"X-VNP-Signature": "deadbeef" * 16},  # 64 bytes hex
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Cryptographic signature verification failed"


def test_vnp_ingestion_valid_signature():
    """Test ingestion succeeds with a valid Ed25519 signature."""
    signing_key = nacl.signing.SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")

    mock_validator = Validator(
        id=uuid.uuid4(), name="Node1", public_key=public_key_hex, status="active"
    )

    payload = {
        "api_id": "api-openai-com",
        "validator_id": "valid-val",
        "region": "us-east-1",
        "latency_ms": 150,
        "http_status_code": 200,
        "success": True,
    }

    message = "api-openai-com:valid-val:us-east-1:150:200:1".encode("utf-8")
    signed = signing_key.sign(message, encoder=HexEncoder)
    signature_hex = signed.signature.decode("utf-8")

    with (
        patch(
            "backend.apps.api.routers.vnp.AsyncSession.get", new_callable=AsyncMock
        ) as mock_get,
        patch(
            "backend.apps.api.routers.vnp.update_api_composite_score",
            new_callable=AsyncMock,
        ) as mock_update,
    ):
        mock_get.return_value = mock_validator
        mock_update.return_value = 99.5

        # Also need to mock commit and add on db
        with (
            patch(
                "backend.apps.api.routers.vnp.AsyncSession.commit",
                new_callable=AsyncMock,
            ),
            patch("backend.apps.api.routers.vnp.AsyncSession.add", MagicMock()),
        ):

            response = client.post(
                "/api/v1/vnp/ingestion",
                json=payload,
                headers={"X-VNP-Signature": signature_hex},
            )

    assert response.status_code == 201
    assert response.json()["status"] == "accepted"
    assert response.json()["new_score"] == 99.5


def test_vnp_beacon_all():
    """Test getting all routes from the beacon."""
    mock_api = MagicMock()
    mock_api.api_id = "test-api"
    mock_api.provider_name = "TestProvider"
    mock_api.endpoint_url = "https://test.com"
    mock_api.current_composite_score = 98.0
    mock_api.stability_rating = "Stable"

    async def mock_execute(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [mock_api]
        return mock_result

    with patch(
        "backend.apps.api.routers.vnp.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=mock_execute,
    ):
        response = client.get("/api/v1/vnp/beacon")

    assert response.status_code == 200
    assert response.json()["network_status"] == "operational"
    assert len(response.json()["routes"]) == 1
    assert response.json()["routes"][0]["api_id"] == "test-api"


def test_vnp_beacon_single():
    """Test getting a single route from the beacon via cache."""
    with patch(
        "backend.apps.api.routers.vnp.get_cached_api_score", new_callable=AsyncMock
    ) as mock_cache:
        mock_cache.return_value = {
            "score": 95.0,
            "rating": "Stable",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/vnp/beacon?api_id=test-api")

    assert response.status_code == 200
    assert response.json()["api_id"] == "test-api"
    assert response.json()["composite_score"] == 95.0
