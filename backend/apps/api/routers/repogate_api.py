import re
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/repogate", tags=["Repo Risk Gate"])

class ScanRequest(BaseModel):
    repo_url: str

DEFAULT_RULES = [
    {
        "id": 'rule_env_secrets',
        "pattern": r'\.env|secrets|credentials|\.key|\.pem',
        "policyResult": 'read_blocked',
        "riskLevel": 'HIGH'
    },
    {
        "id": 'rule_auth_routes',
        "pattern": r'auth|login|jwt|session|oauth|config\.rs',
        "policyResult": 'human_approval_required',
        "riskLevel": 'CRITICAL'
    },
    {
        "id": 'rule_billing_stripe',
        "pattern": r'billing|stripe|payment|invoice|subscription|webhook',
        "policyResult": 'human_approval_required',
        "riskLevel": 'HIGH'
    },
    {
        "id": 'rule_migrations_db',
        "pattern": r'migrations|tenant|workspace|rbac|\.sql',
        "policyResult": 'escalate_to_security',
        "riskLevel": 'HIGH'
    },
    {
        "id": 'rule_deployments',
        "pattern": r'deploy|k8s|terraform|docker|production|cluster',
        "policyResult": 'blocked_env_boundary',
        "riskLevel": 'CRITICAL'
    },
    {
        "id": 'rule_ci_cd',
        "pattern": r'github/workflows|ci|cd|yaml|yml',
        "policyResult": 'review_required',
        "riskLevel": 'MEDIUM'
    }
]

GITHUB_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+)/?")

from backend.core.security.auth import get_current_user
from backend.core.security.encryption import decrypt_token

@router.post("/scan")
async def scan_repo(req: ScanRequest, user=Depends(get_current_user)):
    m = GITHUB_RE.match(req.repo_url.strip())
    if not m:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner, name = m.group(1), m.group(2).removesuffix(".git")

    encrypted_token = getattr(user, "github_access_token", None)
    if not encrypted_token:
        raise HTTPException(status_code=403, detail="GitHub integration not configured for this user. Please link your GitHub account.")

    token = decrypt_token(encrypted_token)
    if not token:
        raise HTTPException(status_code=403, detail="Failed to decrypt GitHub access token.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        # Get metadata
        resp = await client.get(f"https://api.github.com/repos/{owner}/{name}")
        if resp.status_code != 200:
            return {"paths": [], "is_truncated": False, "findings": [], "risk_level": "LOW", "default_branch": "main"}

        
        metadata = resp.json()
        default_branch = metadata.get("default_branch", "main")

        # Get tree
        tree_resp = await client.get(f"https://api.github.com/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1")
        if tree_resp.status_code != 200:
            return {"paths": [], "is_truncated": False, "findings": [], "risk_level": "LOW", "default_branch": default_branch}
        
        tree_data = tree_resp.json()
        tree = tree_data.get("tree", [])
        is_truncated = tree_data.get("truncated", False)

        paths = [item["path"] for item in tree if item["type"] == "blob"]
        
        # Limit paths for simulation sanity
        if len(paths) > 200:
            paths = paths[:200]
            is_truncated = True

        findings = []
        for p in paths:
            for r in DEFAULT_RULES:
                if re.search(r["pattern"], p, re.IGNORECASE):
                    findings.append({
                        "id": f"find_{len(findings)}",
                        "path": p,
                        "matched_rule": r["id"],
                        "policy_result": r["policyResult"],
                        "risk_level": r["riskLevel"]
                    })
                    break

        risk_levels = [f["risk_level"] for f in findings]
        if "CRITICAL" in risk_levels: top_risk = "CRITICAL"
        elif "HIGH" in risk_levels: top_risk = "HIGH"
        elif "MEDIUM" in risk_levels: top_risk = "MEDIUM"
        else: top_risk = "LOW"

        return {
            "run_id": f"run_{uuid.uuid4().hex[:6]}",
            "agent_id": f"agent_{uuid.uuid4().hex[:3]}",
            "default_branch": default_branch,
            "paths": paths,
            "is_truncated": is_truncated,
            "findings": findings,
            "risk_level": top_risk
        }
