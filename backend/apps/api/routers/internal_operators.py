"""UACP V3 Worker Registry"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.core.security.auth import get_current_user

router = APIRouter(
    prefix="/internal/operators",
    tags=["uacp-operators"]
)

async def require_superuser(user=Depends(get_current_user)):
    """Only superusers or automation keys can access the registry."""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser or AUTOMATION scope required"
        )
    return user

WORKER_REGISTRY = {
    "workers": {
        "herald": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "harvest": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "bouncer": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "gauge": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "arbiter": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        
        "ledger": {"pillar": "governance", "committees": ["governance-evidence"], "ready": True},
        "oracle": {"pillar": "governance", "committees": ["governance-evidence"], "ready": True},
        "builder-arbiter": {"pillar": "governance", "committees": ["governance-evidence", "builder-systems"], "ready": True},
        "sheriff": {"pillar": "governance", "committees": ["governance-evidence", "experience-assurance"], "ready": True},
        
        "signal": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "scout": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "mint": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "welcome": {"pillar": "intelligence", "committees": ["growth-intelligence", "experience-assurance"], "ready": True},
        
        "builder-scout": {"pillar": "builder", "committees": ["builder-systems"], "ready": False},
        "builder-forge": {"pillar": "builder", "committees": ["builder-systems"], "ready": False},
        
        "sentinel": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "mirror": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "polish": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "glide": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "pulse": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
    },
    "committees": [
        "marketplace-operations",
        "governance-evidence",
        "growth-intelligence",
        "builder-systems",
        "experience-assurance"
    ],
    "minimum_live_set": [
        "gauge", "ledger", "sentinel", "mirror", "pulse", "sheriff", "polish"
    ],
    "promotion_logic": "Require Archives write for promotion."
}

@router.get("/registry")
async def get_worker_registry(user=Depends(require_superuser)):
    """Returns the internal UACP V3 Worker Registry."""
    return WORKER_REGISTRY
