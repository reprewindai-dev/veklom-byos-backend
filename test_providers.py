import urllib.request, urllib.error, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get token
req1 = urllib.request.Request("http://localhost:80/api/v1/auth/eval-session", method="POST")
req1.add_header("Content-Type", "application/json")
resp1 = urllib.request.urlopen(req1, data=b"{}", timeout=15, context=ctx)
token = json.load(resp1)["access_token"]

# Get provider status
req2 = urllib.request.Request("http://localhost:80/api/v1/providers/routing/status")
req2.add_header("Authorization", f"Bearer {token}")
resp2 = urllib.request.urlopen(req2, timeout=15, context=ctx)
data = json.load(resp2)

for name, status in data.get("providers", {}).items():
    print(f"{name}: available={status.get('available')}, source={status.get('source')}")
