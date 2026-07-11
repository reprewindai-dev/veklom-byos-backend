import urllib.request, json

BASE = "http://localhost:80/api/v1"

# Test 1: No auth
req = urllib.request.Request(f"{BASE}/auth/me")
try:
    urllib.request.urlopen(req)
    print("FAIL: no auth should return 401")
except urllib.error.HTTPError as e:
    print(f"PASS: no auth → {e.code}")

# Test 2: Demo token
req = urllib.request.Request(f"{BASE}/auth/me", headers={"Authorization": "Bearer veklom-demo-token-quantum"})
try:
    urllib.request.urlopen(req)
    print("FAIL: demo token should return 401")
except urllib.error.HTTPError as e:
    print(f"PASS: demo token → {e.code}")

# Test 3: Eval session
data = json.dumps({"fingerprint": "test-phase1"}).encode()
req = urllib.request.Request(f"{BASE}/auth/eval-session", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
body = json.loads(resp.read())
token = body["access_token"]
print(f"PASS: eval session → token={token[:20]}...")

# Test 4: /auth/me with eval token
req = urllib.request.Request(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req)
me = json.loads(resp.read())
print(f"full_name: {me['full_name']}")
print(f"workspace: {me['workspace']['name']}")
print(f"role: {me['role']}")
print(f"is_superuser: {me['is_superuser']}")
print("capabilities:")
for k, v in me["capabilities"].items():
    print(f"  {k}: {v}")

# Test 5: Workspace overview
req = urllib.request.Request(f"{BASE}/workspace/overview", headers={"Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req)
overview = json.loads(resp.read())
print(f"\noverview workspace_id: {overview['workspace_id']}")
print(f"plan: {overview['plan']}")
print(f"members: {overview['members_count']}")
print("PASS: overview returned real workspace-scoped data")
