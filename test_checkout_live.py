import requests

BASE_URL = "https://veklom.com/api/v1"

# 1. Get eval session
resp = requests.post(f"{BASE_URL}/auth/eval-session", json={"fingerprint": "test_script_checkout_123"})
data = resp.json()
token = data.get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. Test Checkout for Marketplace (mocking a listing checkout)
checkout_resp = requests.post(
    f"{BASE_URL}/subscriptions/checkout",
    headers=headers,
    json={
        "plan_id": "marketplace_item",
        "amount": "49.99",
        "listing_id": "ls_test_123"
    }
)

print("Checkout Status:", checkout_resp.status_code)
if checkout_resp.status_code == 200:
    print("Checkout URL:", checkout_resp.json())
else:
    print("Checkout Error:", checkout_resp.text)
