import json, subprocess

body = json.dumps({"fingerprint": "test-p1"})
result = subprocess.run(
    ["curl", "-s", "-X", "POST", "http://localhost:8088/api/v1/auth/eval-session",
     "-H", "Content-Type: application/json", "-d", body],
    capture_output=True, text=True
)
print("RAW:", result.stdout[:500])
