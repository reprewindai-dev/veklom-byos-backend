"""Authority service for Veklom Runtime Authority Pack."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.authority import AuthorityBundle, AuthorityRun, AuthorityDecision
from backend.db.models.agent import Agent
from backend.db.models.lineage import BirthCertificate, LineageEdge
from backend.db.models.user import User


class AuthorityContext:
    """Aggregated authority context for an agent or workspace."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        authority_run_id: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.authority_run_id = authority_run_id
        
        # Aggregated data
        self.agent_info: Optional[Dict[str, Any]] = None
        self.birth_certificate: Optional[Dict[str, Any]] = None
        self.lineage: List[Dict[str, Any]] = []
        self.authority_bundle: Optional[Dict[str, Any]] = None
        self.active_run: Optional[Dict[str, Any]] = None
        self.recent_decisions: List[Dict[str, Any]] = []
        self.permissions_summary: Dict[str, Any] = {}
        self.risk_assessment: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "agent_id": self.agent_id,
            "workspace_id": self.workspace_id,
            "authority_run_id": self.authority_run_id,
            "agent_info": self.agent_info,
            "birth_certificate": self.birth_certificate,
            "lineage": self.lineage,
            "authority_bundle": self.authority_bundle,
            "active_run": self.active_run,
            "recent_decisions": self.recent_decisions,
            "permissions_summary": self.permissions_summary,
            "risk_assessment": self.risk_assessment,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


class AuthorityService:
    """Service for managing authority contexts and aggregation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_authority_context(
        self,
        agent_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        authority_run_id: Optional[str] = None
    ) -> AuthorityContext:
        """Build aggregated authority context."""
        
        context = AuthorityContext(
            agent_id=agent_id,
            workspace_id=workspace_id,
            authority_run_id=authority_run_id
        )
        
        # If authority_run_id provided, use it as primary key
        if authority_run_id:
            await self._load_run_context(context)
        elif agent_id:
            await self._load_agent_context(context)
        elif workspace_id:
            await self._load_workspace_context(context)
        else:
            raise ValueError("Must provide either agent_id, workspace_id, or authority_run_id")
        
        return context
    
    async def _load_run_context(self, context: AuthorityContext) -> None:
        """Load context from authority run."""
        
        # Get the authority run
        run_result = await self.db.execute(
            select(AuthorityRun).where(AuthorityRun.id == context.authority_run_id)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            return
        
        context.active_run = {
            "id": run.id,
            "status": run.status,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "total_actions": run.total_actions,
            "approved_actions": run.approved_actions,
            "denied_actions": run.denied_actions,
            "violation_count": run.violation_count,
            "decisions": run.decisions,
            "violations": run.violations,
            "approvals": run.approvals
        }
        
        # Load related data
        context.agent_id = run.agent_id
        context.workspace_id = run.workspace_id
        
        await self._load_agent_info(context)
        await self._load_authority_bundle(run.authority_bundle_id, context)
        await self._load_recent_decisions(run.id, context)
        await self._build_permissions_summary(context)
        await self._build_risk_assessment(context)
    
    async def _load_agent_context(self, context: AuthorityContext) -> None:
        """Load context from agent."""
        
        await self._load_agent_info(context)
        await self._load_birth_certificate(context)
        await self._load_lineage(context)
        
        # Get active authority run for this agent
        run_result = await self.db.execute(
            select(AuthorityRun)
            .where(AuthorityRun.agent_id == context.agent_id)
            .where(AuthorityRun.status == "active")
            .order_by(AuthorityRun.created_at.desc())
            .limit(1)
        )
        run = run_result.scalar_one_or_none()
        
        if run:
            context.authority_run_id = run.id
            await self._load_authority_bundle(run.authority_bundle_id, context)
            await self._load_recent_decisions(run.id, context)
        
        await self._build_permissions_summary(context)
        await self._build_risk_assessment(context)
    
    async def _load_workspace_context(self, context: AuthorityContext) -> None:
        """Load context from workspace."""
        
        # Get active authority bundles for workspace
        bundle_result = await self.db.execute(
            select(AuthorityBundle)
            .where(AuthorityBundle.workspace_id == context.workspace_id)
            .where(AuthorityBundle.is_active == True)
            .order_by(AuthorityBundle.created_at.desc())
            .limit(1)
        )
        bundle = bundle_result.scalar_one_or_none()
        
        if bundle:
            await self._load_authority_bundle(bundle.id, context)
        
        await self._build_permissions_summary(context)
        await self._build_risk_assessment(context)
    
    async def _load_agent_info(self, context: AuthorityContext) -> None:
        """Load basic agent information."""
        
        if not context.agent_id:
            return
        
        agent_result = await self.db.execute(
            select(Agent).where(Agent.agent_id == context.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if agent:
            context.agent_info = {
                "id": agent.agent_id,
                "name": agent.name,
                "creator": agent.creator,
                "jurisdiction": agent.jurisdiction,
                "declared_purpose": agent.declared_purpose,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            }
    
    async def _load_birth_certificate(self, context: AuthorityContext) -> None:
        """Load birth certificate for agent."""
        
        if not context.agent_id:
            return
        
        # Get agent record first
        agent_result = await self.db.execute(
            select(Agent).where(Agent.agent_id == context.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            return
        
        cert_result = await self.db.execute(
            select(BirthCertificate).where(BirthCertificate.agent_id == agent.id)
        )
        cert = cert_result.scalar_one_or_none()
        
        if cert:
            context.birth_certificate = {
                "certificate_id": cert.certificate_id,
                "genome_hash": cert.genome_hash,
                "document_uri": cert.document_uri,
                "parent_agent_ids": cert.parent_agent_ids,
                "issued_at": cert.issued_at.isoformat() if cert.issued_at else None
            }
    
    async def _load_lineage(self, context: AuthorityContext) -> None:
        """Load agent lineage information."""
        
        if not context.agent_id:
            return
        
        # Get agent record first
        agent_result = await self.db.execute(
            select(Agent).where(Agent.agent_id == context.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            return
        
        # Get parent relationships
        parent_result = await self.db.execute(
            select(LineageEdge, Agent)
            .join(Agent, LineageEdge.parent_agent_id == Agent.id)
            .where(LineageEdge.child_agent_id == agent.id)
        )
        
        for edge, parent in parent_result.all():
            context.lineage.append({
                "type": "parent",
                "agent_id": parent.agent_id,
                "name": parent.name,
                "relationship": "parent_of",
                "created_at": edge.created_at.isoformat() if edge.created_at else None
            })
        
        # Get child relationships
        child_result = await self.db.execute(
            select(LineageEdge, Agent)
            .join(Agent, LineageEdge.child_agent_id == Agent.id)
            .where(LineageEdge.parent_agent_id == agent.id)
        )
        
        for edge, child in child_result.all():
            context.lineage.append({
                "type": "child",
                "agent_id": child.agent_id,
                "name": child.name,
                "relationship": "child_of",
                "created_at": edge.created_at.isoformat() if edge.created_at else None
            })
    
    async def _load_authority_bundle(
        self, 
        bundle_id: str, 
        context: AuthorityContext
    ) -> None:
        """Load authority bundle information."""
        
        bundle_result = await self.db.execute(
            select(AuthorityBundle).where(AuthorityBundle.id == bundle_id)
        )
        bundle = bundle_result.scalar_one_or_none()
        
        if bundle:
            context.authority_bundle = {
                "id": bundle.id,
                "name": bundle.name,
                "version": bundle.version,
                "risk_level": bundle.risk_level,
                "tool_permissions": bundle.tool_permissions,
                "workspace_restrictions": bundle.workspace_restrictions,
                "time_restrictions": bundle.time_restrictions,
                "description": bundle.description,
                "tags": bundle.tags,
                "created_at": bundle.created_at.isoformat() if bundle.created_at else None
            }
    
    async def _load_recent_decisions(
        self, 
        run_id: str, 
        context: AuthorityContext
    ) -> None:
        """Load recent authority decisions."""
        
        decisions_result = await self.db.execute(
            select(AuthorityDecision)
            .where(AuthorityDecision.authority_run_id == run_id)
            .order_by(AuthorityDecision.decision_time.desc())
            .limit(50)
        )
        
        for decision in decisions_result.scalars().all():
            context.recent_decisions.append({
                "id": decision.id,
                "tool_name": decision.tool_name,
                "decision": decision.decision,
                "reason": decision.reason,
                "confidence_score": decision.confidence_score,
                "decision_time": decision.decision_time.isoformat() if decision.decision_time else None,
                "risk_assessment": decision.risk_assessment,
                "evidence_refs": decision.evidence_refs
            })
    
    async def _build_permissions_summary(self, context: AuthorityContext) -> None:
        """Build permissions summary from authority bundle."""
        
        if not context.authority_bundle:
            return
        
        permissions = context.authority_bundle.get("tool_permissions", {})
        
        # Count permissions by type
        approved_tools = []
        denied_tools = []
        conditional_tools = []
        
        for tool, config in permissions.items():
            if isinstance(config, dict):
                if config.get("allowed", False):
                    approved_tools.append(tool)
                elif config.get("allowed") is False:
                    denied_tools.append(tool)
                else:
                    conditional_tools.append(tool)
            elif config is True:
                approved_tools.append(tool)
            elif config is False:
                denied_tools.append(tool)
        
        context.permissions_summary = {
            "total_tools": len(permissions),
            "approved_tools": approved_tools,
            "denied_tools": denied_tools,
            "conditional_tools": conditional_tools,
            "workspace_restrictions": context.authority_bundle.get("workspace_restrictions", {}),
            "time_restrictions": context.authority_bundle.get("time_restrictions", {})
        }
    
    async def _build_risk_assessment(self, context: AuthorityContext) -> None:
        """Build risk assessment for the context."""
        
        risk_level = "medium"
        risk_factors = []
        
        # Check authority bundle risk level
        if context.authority_bundle:
            risk_level = context.authority_bundle.get("risk_level", "medium")
        
        # Check recent violations
        if context.active_run:
            violation_count = context.active_run.get("violation_count", 0)
            if violation_count > 5:
                risk_factors.append("high_violation_count")
                risk_level = "high"
            elif violation_count > 0:
                risk_factors.append("violations_detected")
        
        # Check denied actions
        if context.active_run:
            denied_ratio = context.active_run.get("denied_actions", 0) / max(context.active_run.get("total_actions", 1), 1)
            if denied_ratio > 0.3:
                risk_factors.append("high_denial_rate")
                risk_level = "high"
            elif denied_ratio > 0.1:
                risk_factors.append("elevated_denial_rate")
        
        # Check agent lineage complexity
        if len(context.lineage) > 10:
            risk_factors.append("complex_lineage")
        
        context.risk_assessment = {
            "overall_risk_level": risk_level,
            "risk_factors": risk_factors,
            "confidence_score": 0.85 if risk_level == "low" else 0.70 if risk_level == "medium" else 0.50,
            "last_assessed": datetime.now(timezone.utc).isoformat()
        }
