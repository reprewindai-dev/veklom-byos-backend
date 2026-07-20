from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_cors_allowed_origin():
    response = client.options(
        "/api/v1/onboard",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_cors_disallowed_origin():
    response = client.options(
        "/api/v1/onboard",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Fastapi/Starlette CORSMiddleware returns a 400 Bad Request for disallowed origins
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers or response.headers.get("access-control-allow-origin") != "http://evil.com"
