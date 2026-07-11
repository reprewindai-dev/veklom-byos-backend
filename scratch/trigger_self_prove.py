
import httpx
import json

resp = httpx.post("https://api.veklom.com/api/v1/banker/self-prove", timeout=20.0)
print(f"Status: {resp.status_code}")
try:
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(resp.text)

