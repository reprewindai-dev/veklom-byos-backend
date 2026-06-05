import requests

BASE_URL = "https://veklom.com/api/v1"

# 1. Get eval session
resp = requests.post(f"{BASE_URL}/auth/eval-session", json={"fingerprint": "test_script_123"})
if resp.status_code != 200:
    print("Eval session failed:", resp.text)
    exit(1)

data = resp.json()
token = data.get("access_token")
print("Got token:", token[:15] + "...")

headers = {"Authorization": f"Bearer {token}"}

# 2. Test /auth/me
me_resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print("Auth/Me Status:", me_resp.status_code)
if me_resp.status_code != 200:
    print("Auth/Me Error:", me_resp.text)

# 3. Test /subscriptions/current
sub_resp = requests.get(f"{BASE_URL}/subscriptions/current", headers=headers)
print("Sub/Current Status:", sub_resp.status_code)
if sub_resp.status_code == 200:
    print("Sub/Current Data:", sub_resp.json())
else:
    print("Sub/Current Error:", sub_resp.text)
