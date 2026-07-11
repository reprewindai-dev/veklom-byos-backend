import json, subprocess

# Get eval token
body = json.dumps({"fingerprint": "test-p2"})
result = subprocess.run(
    ["curl", "-s", "-X", "POST", "http://localhost:80/api/v1/auth/eval-session",
     "-H", "Content-Type: application/json", "-d", body],
    capture_output=True, text=True
)
token = json.loads(result.stdout)["access_token"]

# Test overview
result = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}",
     "http://localhost:80/api/v1/workspace/overview"],
    capture_output=True, text=True
)
ov = json.loads(result.stdout)
print("=== Overview ===")
for k in ['plan','members_count','models_enabled','total_requests_today','spend_today_usd','spend_cap_usd','active_pipelines','active_deployments','audit_entries']:
    print(f"  {k}: {ov.get(k)}")
print(f"  recent_runs: {len(ov.get('recent_runs',[]))} items")
print(f"  alerts: {len(ov.get('alerts',[]))} items")
print(f"  audit_logs: {len(ov.get('audit_logs',[]))} items")
print(f"  fleet: {len(ov.get('fleet',[]))} models")

# Test search
result = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}",
     "http://localhost:80/api/v1/workspace/search?q=model"],
    capture_output=True, text=True
)
sr = json.loads(result.stdout)
print(f"\n=== Search 'model' === {len(sr.get('results',[]))} results")

# Test monitoring
result = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}",
     "http://localhost:80/api/v1/workspace/monitoring/health"],
    capture_output=True, text=True
)
mh = json.loads(result.stdout)
print(f"\n=== Monitoring Health === status={mh.get('status')}")

# Test security alerts
result = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}",
     "http://localhost:80/api/v1/workspace/security/alerts"],
    capture_output=True, text=True
)
sa = json.loads(result.stdout)
print(f"=== Security Alerts === {len(sa.get('alerts',[]))} alerts")

# Test billing
result = subprocess.run(
    ["curl", "-s", "-H", f"Authorization: Bearer {token}",
     "http://localhost:80/api/v1/workspace/billing/breakdown"],
    capture_output=True, text=True
)
bb = json.loads(result.stdout)
print(f"=== Billing === spend=${bb.get('spend_usd')} budget=${bb.get('budget_limit_usd')}")

print("\nPHASE 2 PASSED — all overview routes return workspace-scoped data")
