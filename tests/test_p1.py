import json, subprocess

body = json.dumps({"fingerprint": "test-p1"})
with open("/tmp/eval-body.json", "w") as f:
    f.write(body)

result = subprocess.run(
    ["curl", "-s", "-X", "POST", "http://localhost:8088/api/v1/auth/eval-session",
     "-H", "Content-Type: application/json", "-d", "@/tmp/eval-body.json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
token = data["access_token"]
print(f"Token: {token[:30]}... User: {data['user']['full_name']} Plan: {data['plan']}")

result2 = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}", "http://localhost:8088/api/v1/auth/me"],
    capture_output=True, text=True
)
me = json.loads(result2.stdout)
print(f"full_name: {me['full_name']} workspace: {me['workspace']['name']} role: {me['role']} superuser: {me['is_superuser']}")
for k, v in me["capabilities"].items():
    print(f"  {k}: {v}")

result3 = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}", "http://localhost:8088/api/v1/workspace/overview"],
    capture_output=True, text=True
)
ov = json.loads(result3.stdout)
print(f"overview: ws={ov['workspace_id']} plan={ov['plan']} members={ov['members_count']}")
print("PHASE 1 PASSED")
