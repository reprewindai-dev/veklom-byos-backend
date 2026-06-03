"""Entitlement plan verification dependencies and rich entitlement decisions."""
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security.auth import get_current_user
from backend.core.database.database import get_db

logger = logging.getLogger(__name__)

# Plan hierarchy levels for normalization:
#   free       = 0 (Free Evaluation)
#   founding   = 1 (Founding Activation / Starter)
#   standard   = 2 (Standard Plan / Pro)
#   regulated  = 3 (Regulated / Enterprise / Sovereign)
#
PLAN_LEVELS = {
    "free": 0,
    "founding": 1,
    "standard": 2,
    "regulated": 3
}

PLAN_NORMALIZATION = {
    "free": "free",
    "free_evaluation": "free",
    "starter": "founding",
    "founding": "founding",
    "pro": "standard",
    "standard": "standard",
    "sovereign": "regulated",
    "regulated": "regulated",
    "enterprise": "regulated"
}

# Plan hierarchy mapping to preserve backward compatibility with starter/pro/sovereign:
PLAN_HIERARCHY = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "sovereign": 3,
    "enterprise": 4
}


class RecommendedUpgrade(BaseModel):
    tier: str
    headline: str
    cta: str


class MarketplaceAlternative(BaseModel):
    moduleId: str
    name: str
    price: str
    note: str


class UsageContext(BaseModel):
    freeRunsUsed: int
    freeRunsLimit: int
    attemptedFeatureCount: int
    estimatedRunCost: Optional[float] = None


class EntitlementDecision(BaseModel):
    canView: bool
    canPreview: bool
    canExecute: bool

    currentTier: str  # "free" | "founding" | "standard" | "regulated"
    requiredTier: Optional[str] = None  # "founding" | "standard" | "regulated"

    gateType: str  # "quota_gate" | "feature_gate" | "marketplace_gate" | "risk_gate" | "reserve_gate"

    action: str
    reason: str

    benefits: List[str]
    bestFor: List[str]

    recommendedUpgrade: Optional[RecommendedUpgrade] = None
    marketplaceAlternative: Optional[MarketplaceAlternative] = None
    usageContext: Optional[UsageContext] = None


def _plan_from_role(role: str) -> str:
    """Return a conservative role-based plan fallback.

    OWNER maps to free because workspace ownership alone does not imply a paid
    subscription. The real plan must be read from the Subscription table.
    SUPER_ADMIN keeps sovereign because it is the platform-level role, not a
    self-registered tenant role.
    """
    role = (role or "").upper()
    if role == "SUPER_ADMIN":
        return "sovereign"
    if role in ("USER", "ANALYST"):
        return "starter"
    # OWNER, ADMIN, VIEWER, and unknown roles -> free (conservative default)
    return "free"


def require_entitlement(required_plan: str):
    """Dependency that enforces subscription tier requirements.

    Derives the effective plan from the user's role as a conservative fallback.
    Free-tier (eval) users are allowed on starter-level endpoints (playground,
    models) but warned. Pro/sovereign features require an active subscription.
    """

    async def _entitlement_checker(user=Depends(get_current_user)):
        current_plan = _plan_from_role(getattr(user, "role", ""))

        req_level = PLAN_HIERARCHY.get(required_plan, 0)
        cur_level = PLAN_HIERARCHY.get(current_plan, 0)

        if cur_level < req_level:
            # Free users can still access starter endpoints (playground etc.)
            # but log the violation. Block only for pro/sovereign features.
            if cur_level == 0 and req_level <= 1:
                logger.info(
                    f"[ENTITLEMENT_FREE_ACCESS] User {user.id} (free) accessing "
                    f"starter endpoint. Allowing."
                )
            else:
                logger.warning(
                    f"[ENTITLEMENT_BLOCKED] User {user.id} plan={current_plan} "
                    f"tried {required_plan}."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"This feature requires the {required_plan} plan. "
                        f"Current: {current_plan}. "
                        "Visit /workspace/#/billing to upgrade."
                    ),
                )
        return user

    return _entitlement_checker


# Details for all gates/actions:
GATED_ACTIONS = {
    "production_run": {
        "required_tier": "founding",
        "gate_type": "quota_gate",
        "reason": "You are trying to execute a production governed run.",
        "benefits": ["Production run limits", "Saved prompts", "Custom endpoints"],
        "best_for": ["Builders who want to move from evaluation into real operation."],
        "recommended_upgrade": {
            "tier": "founding",
            "headline": "Activate Founding Workspace",
            "cta": "Activate"
        }
    },
    "deploy": {
        "required_tier": "standard",
        "gate_type": "risk_gate",
        "reason": "You are trying to publish a governed endpoint from this workspace.",
        "benefits": ["production deployments", "team approvals", "monitoring", "vault-backed secrets", "deployment evidence"],
        "best_for": ["Teams that need real endpoints, shared workflows, and audit trails."],
        "recommended_upgrade": {
            "tier": "standard",
            "headline": "Production Deployments require Standard",
            "cta": "Upgrade to Standard"
        },
        "marketplace_alternative": {
            "moduleId": "deploy-gate",
            "name": "Buy Deployment Gate standalone",
            "price": "$79/mo",
            "note": "Get included in Standard or buy standalone."
        }
    },
    "install_module": {
        "required_tier": "founding",
        "gate_type": "marketplace_gate",
        "reason": "You are trying to install a marketplace module to your workspace.",
        "benefits": ["Marketplace installs", "Supervised agents", "API keys"],
        "best_for": ["Builders who want custom integrations and tools."],
        "recommended_upgrade": {
            "tier": "founding",
            "headline": "Marketplace Installs require Founding Activation",
            "cta": "Activate Founding"
        }
    },
    "export_signed_evidence": {
        "required_tier": "regulated",
        "gate_type": "feature_gate",
        "reason": "You are trying to generate compliance-grade evidence with consent, identity, integrity, and audit chain attached.",
        "benefits": ["UACP6 compliance", "Auditor dashboard", "Consent catalogs", "Private policy packs"],
        "best_for": ["Healthcare, finance, insurance, government, and compliance-heavy teams."],
        "recommended_upgrade": {
            "tier": "regulated",
            "headline": "Regulated Evidence requires Regulated",
            "cta": "Request Regulated"
        },
        "marketplace_alternative": {
            "moduleId": "auditor-bundle",
            "name": "Buy Auditor Bundle standalone",
            "price": "$299/mo",
            "note": "Get included in Regulated or buy standalone."
        }
    },
    "create_api_key": {
        "required_tier": "founding",
        "gate_type": "feature_gate",
        "reason": "You are trying to create developer API keys.",
        "benefits": ["API key access", "Custom integrations", "CLI connections"],
        "best_for": ["Developers building on top of Veklom."],
        "recommended_upgrade": {
            "tier": "founding",
            "headline": "API Keys require Founding Activation",
            "cta": "Activate Founding"
        }
    },
    "activate_agent": {
        "required_tier": "founding",
        "gate_type": "feature_gate",
        "reason": "You are trying to activate an agent against a real workspace action.",
        "benefits": ["Supervised agents", "ArbiterOS coordination", "Spent controls", "Policy gates"],
        "best_for": ["Builders who want to move from evaluation into real operation."],
        "recommended_upgrade": {
            "tier": "founding",
            "headline": "Supervised Agents require Founding Activation",
            "cta": "Activate Founding Workspace"
        },
        "marketplace_alternative": {
            "moduleId": "agent-packs",
            "name": "Buy Agent Session Pack standalone",
            "price": "$49/mo",
            "note": "Get included in Founding or buy standalone."
        }
    },
    "add_secret": {
        "required_tier": "standard",
        "gate_type": "reserve_gate",
        "reason": "You are trying to add a production secret to the vault.",
        "benefits": ["Vault-backed secrets", "SAML/SCIM integration", "Advanced monitoring"],
        "best_for": ["Teams with security and credentials custody requirements."],
        "recommended_upgrade": {
            "tier": "standard",
            "headline": "Vault Secrets require Standard",
            "cta": "Upgrade to Standard"
        }
    },
    "invite_team_member": {
        "required_tier": "standard",
        "gate_type": "feature_gate",
        "reason": "You are trying to invite a team member to this workspace.",
        "benefits": ["Team controls", "Shared workspace", "Role management"],
        "best_for": ["Teams requiring collaboration and review gates."],
        "recommended_upgrade": {
            "tier": "standard",
            "headline": "Team Management requires Standard",
            "cta": "Upgrade to Standard"
        }
    },
    "schedule_pipeline": {
        "required_tier": "standard",
        "gate_type": "feature_gate",
        "reason": "You are trying to schedule a production pipeline.",
        "benefits": ["Scheduled executions", "Custom trigger thresholds", "E2E evidence collection"],
        "best_for": ["Teams automating regular data and audit flows."],
        "recommended_upgrade": {
            "tier": "standard",
            "headline": "Scheduled Pipelines require Standard",
            "cta": "Upgrade to Standard"
        }
    },
    "execute_terminal_command": {
        "required_tier": "standard",
        "gate_type": "feature_gate",
        "reason": "You are trying to run a production or autonomous terminal command.",
        "benefits": ["Production CLI actions", "Raw API execution", "Autonomous runs"],
        "best_for": ["Teams requiring interactive terminal operations."],
        "recommended_upgrade": {
            "tier": "standard",
            "headline": "Production Commands require Standard",
            "cta": "Upgrade to Standard"
        }
    },
    "regulated_compliance_action": {
        "required_tier": "regulated",
        "gate_type": "risk_gate",
        "reason": "You are trying to generate compliance-grade evidence with consent, identity, and audit chain.",
        "benefits": ["UACP6 compliance", "Auditor dashboard", "Consent catalogs", "Private policy packs"],
        "best_for": ["Healthcare, finance, insurance, government, and compliance-heavy teams."],
        "recommended_upgrade": {
            "tier": "regulated",
            "headline": "Regulated compliance requires Regulated",
            "cta": "Request Regulated"
        }
    }
}


async def get_entitlement_decision(user, action: str, db: AsyncSession = None) -> EntitlementDecision:
    """Return a rich EntitlementDecision structure for any workspace action."""
    # 1. Determine current plan
    db_plan = "free"

    # Try user object directly
    if user:
        if getattr(user, "plan", None):
            db_plan = user.plan.lower()
        elif getattr(user, "role", None):
            db_plan = _plan_from_role(user.role).lower()

    # Query database for workspace license tier if db session is active
    if db and user and getattr(user, "workspace_id", None):
        try:
            from backend.db.models.workspace import Workspace
            ws_stmt = select(Workspace).where(Workspace.id == user.workspace_id)
            ws = (await db.execute(ws_stmt)).scalar_one_or_none()
            if ws and ws.license_tier:
                db_plan = ws.license_tier.lower()
        except Exception:
            pass

    # Normalize plan name
    current_tier = PLAN_NORMALIZATION.get(db_plan, "free")

    # 2. Get Gated Action metadata
    gate_meta = GATED_ACTIONS.get(action)

    # Default fallback for unknown actions: require founding tier
    if not gate_meta:
        gate_meta = {
            "required_tier": "founding",
            "gate_type": "feature_gate",
            "reason": f"This action ({action}) is gated.",
            "benefits": ["Founding level execution capabilities"],
            "best_for": ["Builders moving into production."],
            "recommended_upgrade": {
                "tier": "founding",
                "headline": "Action Gated",
                "cta": "Activate Founding"
            }
        }

    required_tier = gate_meta["required_tier"]
    gate_type = gate_meta["gate_type"]
    reason = gate_meta["reason"]
    benefits = gate_meta["benefits"]
    best_for = gate_meta["best_for"]

    cur_level = PLAN_LEVELS.get(current_tier, 0)
    req_level = PLAN_LEVELS.get(required_tier, 0)
    can_execute = cur_level >= req_level

    # 3. Get free runs usage context
    free_runs_used = 0
    if db and user and getattr(user, "workspace_id", None):
        try:
            from backend.db.models.ai import ExecutionLog
            cnt_stmt = select(func.count()).select_from(ExecutionLog).where(
                ExecutionLog.workspace_id == user.workspace_id
            )
            free_runs_used = (await db.scalar(cnt_stmt)) or 0
        except Exception:
            pass

    # Generate custom proactive insights at specific counts
    custom_headline = None
    if current_tier == "free":
        if free_runs_used >= 12:
            custom_headline = f"You have used {free_runs_used} of 15 free governed runs. Founding unlocks production runs."
        elif free_runs_used >= 8:
            custom_headline = f"You are using checks. Standard may be best because it includes Repo Risk Gates."

    rec_upgrade_data = gate_meta.get("recommended_upgrade")
    recommended_upgrade = None
    if rec_upgrade_data:
        recommended_upgrade = RecommendedUpgrade(
            tier=rec_upgrade_data["tier"],
            headline=custom_headline or rec_upgrade_data["headline"],
            cta=rec_upgrade_data["cta"]
        )

    marketplace_alt_data = gate_meta.get("marketplace_alternative")
    marketplace_alt = None
    if marketplace_alt_data:
        marketplace_alt = MarketplaceAlternative(
            moduleId=marketplace_alt_data["moduleId"],
            name=marketplace_alt_data["name"],
            price=marketplace_alt_data["price"],
            note=marketplace_alt_data["note"]
        )

    usage_ctx = UsageContext(
        freeRunsUsed=free_runs_used,
        freeRunsLimit=15,
        attemptedFeatureCount=free_runs_used + 1,
        estimatedRunCost=0.25 if action == "production_run" else 0.50
    )

    return EntitlementDecision(
        canView=True,         # Navigation is always open
        canPreview=True,      # Preview/sandbox is always open
        canExecute=can_execute,
        currentTier=current_tier,
        requiredTier=required_tier,
        gateType=gate_type,
        action=action,
        reason=reason,
        benefits=benefits,
        bestFor=best_for,
        recommendedUpgrade=recommended_upgrade,
        marketplaceAlternative=marketplace_alt,
        usageContext=usage_ctx
    )
