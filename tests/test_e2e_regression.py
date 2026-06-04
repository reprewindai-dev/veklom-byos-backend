import os
import pytest
import requests
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("TEST_BASE_URL", "https://veklom.com")
API_BASE = f"{BASE_URL}/api/v1"

@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    # Create a quick admin user and get a token if running against local db
    # For now, we'll just inject a dummy token or rely on a script
    # We will populate auth tokens here during tests
    return session

@pytest.fixture(scope="session")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(base_url=BASE_URL)
        yield context
        browser.close()

def test_auth_login_api(api_client):
    # This will test the /auth/login backend schema
    # Setup test user credentials via environment or fixtures
    pass

def test_unverified_user_intercept(browser_context):
    page = browser_context.new_page()
    # Navigate and assert the middleware injection correctly captures the user
    # Assert no infinite spinners
    pass

# --- Phase 2: Core Dashboard / Overview ---

def test_workspace_status_data(api_client):
    """Test GET /api/v1/workspace/status/data"""
    resp = api_client.get(f"{API_BASE}/workspace/status/data")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data
    assert "workspace_id" in data
    assert "role" in data

def test_monitoring_health(api_client):
    """Test GET /api/v1/workspace/monitoring/health"""
    resp = api_client.get(f"{API_BASE}/workspace/monitoring/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data
    assert "checks" in data

def test_monitoring_metrics(api_client):
    """Test GET /api/v1/workspace/monitoring/metrics"""
    resp = api_client.get(f"{API_BASE}/workspace/monitoring/metrics")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "executions_last_24h" in data or "executions" in data

def test_workspace_overview(api_client):
    """Test GET /api/v1/workspace/overview"""
    resp = api_client.get(f"{API_BASE}/workspace/overview")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "total_requests" in data
    assert "recent_runs" in data
    assert "audit_logs" in data

def test_workspace_search(api_client):
    """Test GET /api/v1/workspace/search"""
    resp = api_client.get(f"{API_BASE}/workspace/search?q=test")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "results" in data

# --- Phase 3: Billing, Subscriptions, Marketplace Buyer Flow ---

def test_subscriptions_plans(api_client):
    """Test GET /api/v1/subscriptions/plans"""
    resp = api_client.get(f"{API_BASE}/subscriptions/plans")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "plan_id" in data[0]

def test_subscriptions_current(api_client):
    """Test GET /api/v1/subscriptions/current"""
    # Without token, should return free tier and 200 OK
    resp = api_client.get(f"{API_BASE}/subscriptions/current")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "plan" in data

def test_marketplace_buyer_install_gating(api_client):
    """Test POST /api/v1/marketplace/listings/{listing_id}/install gating"""
    # Assuming "test_listing" is a dummy ID. Without auth, should be 401.
    # With auth, if paid, should be 402 Payment Required without payment method.
    resp = api_client.post(f"{API_BASE}/marketplace/listings/test_listing/install")
    # Will likely return 401 since no token in the session yet
    assert resp.status_code in [401, 403, 404]

# --- Phase 4: Marketplace Vendor / Seller Flow ---

def test_vendor_create(api_client):
    """Test POST /api/v1/marketplace/vendors/create"""
    # Should be 401 without auth
    resp = api_client.post(f"{API_BASE}/marketplace/vendors/create", json={"business_name": "Test Co"})
    assert resp.status_code in [401, 403]

def test_vendor_submit_gating(api_client):
    """Test POST /api/v1/marketplace/listings/{listing_id}/submit gating"""
    # Without payout-ready status, paid listings cannot be submitted
    resp = api_client.post(f"{API_BASE}/marketplace/listings/test_listing/submit")
    assert resp.status_code in [401, 403, 404]

# --- Phase 5: AI Resources ---

def test_playground_inference(api_client):
    """Test POST /api/v1/playground/inference logic"""
    # Without auth
    resp = api_client.post(f"{API_BASE}/playground/inference", json={"message": "hello"})
    assert resp.status_code in [401, 403]

def test_models_catalog(api_client):
    """Test GET /api/v1/ai/models"""
    resp = api_client.get(f"{API_BASE}/ai/models")
    assert resp.status_code in [200, 401, 403]

# --- Phase 6: Operations & Compliance ---

def test_team_members(api_client):
    """Test GET /api/v1/team/members"""
    resp = api_client.get(f"{API_BASE}/team/members")
    assert resp.status_code in [200, 401]

def test_security_vault(api_client):
    """Test GET /api/v1/security/vault"""
    resp = api_client.get(f"{API_BASE}/security/vault")
    assert resp.status_code in [200, 401]

def test_compliance_report(api_client):
    """Test GET /api/v1/compliance/report"""
    resp = api_client.get(f"{API_BASE}/compliance/report")
    assert resp.status_code in [200, 401, 403]
