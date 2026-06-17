"""
Veklom Agent Registry — Ground truth for all 120 agents.
Used by Agent-000 to distribute assignments and track status.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json

class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class AgentRank(str, Enum):
    RECRUIT = "recruit"          # 0-49 pts
    OPERATIVE = "operative"      # 50-99 pts
    SPECIALIST = "specialist"    # 100-199 pts
    ELITE = "elite"              # 200-349 pts
    COMMANDER = "commander"      # 350-499 pts
    SOVEREIGN = "sovereign"      # 500+ pts

@dataclass
class Agent:
    id: str
    name: str
    phase: str
    committee: str
    priority: str
    mission_file: str
    status: AgentStatus = AgentStatus.IDLE
    rank: AgentRank = AgentRank.RECRUIT
    rank_points: int = 0
    active_penalties: list = field(default_factory=list)
    violations: list = field(default_factory=list)
    completed_tasks: int = 0
    current_task: Optional[str] = None

# Full 120-agent registry
AGENT_REGISTRY = [
    Agent("000", "COMMANDER", "phase0", "Governance", "SOVEREIGN", "agents/phase0-scaffolding/agent-000-commander.md", rank=AgentRank.COMMANDER),
    Agent("001", "STRIPE CONNECT ENGINEER", "phase1", "Engineering", "CRITICAL", "agents/phase1-engineering/agent-001-stripe-connect.md"),
    Agent("002", "REFERRAL SYSTEM ENGINEER", "phase1", "Engineering", "CRITICAL", "agents/phase1-engineering/agent-002-referral-system.md"),
    Agent("003", "UX COMPLETION ENGINEER", "phase1", "Engineering", "HIGH", "agents/phase1-engineering/agent-003-ux-completion.md"),
    Agent("004", "PLAYGROUND ENGINEER", "phase1", "Engineering", "HIGH", "agents/phase1-engineering/agent-004-playground.md"),
    Agent("005", "ONBOARDING ENGINEER", "phase1", "Engineering", "HIGH", "agents/phase1-engineering/agent-005-onboarding.md"),
    Agent("006", "API DOCS ENGINEER", "phase1", "Engineering", "MEDIUM", "agents/phase1-engineering/agent-006-api-docs.md"),
    Agent("007", "PERFORMANCE ENGINEER", "phase1", "Engineering", "MEDIUM", "agents/phase1-engineering/agent-007-performance.md"),
    Agent("008", "SECURITY ENGINEER", "phase1", "Engineering", "HIGH", "agents/phase1-engineering/agent-008-security.md"),
    # Vendor hunters 010-031
    *[Agent(str(i).zfill(3), f"VENDOR HUNTER {i}", "phase2", "Growth", "HIGH", f"agents/phase2-vendor-acquisition/agent-{str(i).zfill(3)}-vendor-hunter.md") for i in range(10, 30)],
    Agent("030", "VENDOR OUTREACH LEAD", "phase2", "Growth", "CRITICAL", "agents/phase2-vendor-acquisition/agent-030-vendor-outreach-lead.md"),
    Agent("031", "VENDOR SUCCESS MANAGER", "phase2", "Growth", "HIGH", "agents/phase2-vendor-acquisition/agent-031-vendor-success.md"),
    # User acquisition 040-044
    Agent("040", "SEO AGENT", "phase3", "Growth", "HIGH", "agents/phase3-user-acquisition/agent-040-seo.md"),
    Agent("041", "CONTENT AGENT", "phase3", "Growth", "HIGH", "agents/phase3-user-acquisition/agent-041-content.md"),
    Agent("042", "COMMUNITY AGENT", "phase3", "Growth", "HIGH", "agents/phase3-user-acquisition/agent-042-community.md"),
    Agent("043", "PAID GROWTH AGENT", "phase3", "Growth", "MEDIUM", "agents/phase3-user-acquisition/agent-043-paid-growth.md"),
    Agent("044", "PRODUCT HUNT LAUNCH AGENT", "phase3", "Growth", "HIGH", "agents/phase3-user-acquisition/agent-044-product-hunt.md"),
    # Retention 050-053
    Agent("050", "PRICING AGENT", "phase4", "Revenue", "CRITICAL", "agents/phase4-retention-revenue/agent-050-pricing.md"),
    Agent("051", "REFERRAL ACTIVATION AGENT", "phase4", "Revenue", "HIGH", "agents/phase4-retention-revenue/agent-051-referral-activation.md"),
    Agent("052", "EMAIL AUTOMATION AGENT", "phase4", "Revenue", "HIGH", "agents/phase4-retention-revenue/agent-052-email-automation.md"),
    Agent("053", "ANALYTICS AGENT", "phase4", "Revenue", "HIGH", "agents/phase4-retention-revenue/agent-053-analytics.md"),
    # Daily ops 060-062
    Agent("060", "SUPPORT AGENT", "phase5", "Operations", "HIGH", "agents/phase5-daily-operations/agent-060-support.md"),
    Agent("061", "MONITORING AGENT", "phase5", "Operations", "CRITICAL", "agents/phase5-daily-operations/agent-061-monitoring.md"),
    Agent("062", "CONTENT CALENDAR AGENT", "phase5", "Operations", "MEDIUM", "agents/phase5-daily-operations/agent-062-content-calendar.md"),
    # Research 063-072
    *[Agent(str(i).zfill(3), f"SCIENTIST {i}", "phase5", "Research", "MEDIUM", f"agents/phase5-daily-operations/agent-{str(i).zfill(3)}-scientist.md") for i in range(63, 73)],
    # Governance 073-079
    *[Agent(str(i).zfill(3), f"DELEGATE {i}", "phase5", "Governance", "HIGH", f"agents/phase5-daily-operations/agent-{str(i).zfill(3)}-delegate.md") for i in range(73, 78)],
    Agent("078", "COUNCIL SECRETARY", "phase5", "Governance", "MEDIUM", "agents/phase5-daily-operations/agent-078-council-secretary.md"),
    Agent("079", "COMPLIANCE OFFICER", "phase5", "Governance", "HIGH", "agents/phase5-daily-operations/agent-079-compliance-officer.md"),
    # QA 080-089
    *[Agent(str(i).zfill(3), f"QA AGENT {i}", "phase5", "Engineering", "HIGH", f"agents/phase5-daily-operations/agent-{str(i).zfill(3)}-qa.md") for i in range(80, 90)],
    # Browser 090-093
    *[Agent(str(i).zfill(3), f"BROWSER AGENT {i}", "phase5", "Engineering", "HIGH", f"agents/phase5-daily-operations/agent-{str(i).zfill(3)}-browser.md") for i in range(90, 94)],
    # Crawlers 094-097
    *[Agent(str(i).zfill(3), f"CRAWLER AGENT {i}", "phase5", "Growth", "HIGH", f"agents/phase5-daily-operations/agent-{str(i).zfill(3)}-crawler.md") for i in range(94, 98)],
    # Visual 098-101
    *[Agent(str(i).zfill(3), f"VISUAL AGENT {i}", "eyes-visual", "Operations", "HIGH", f"agents/eyes-visual/agent-{str(i).zfill(3)}-visual.md") for i in range(98, 102)],
    # Security 102-107
    *[Agent(str(i).zfill(3), f"SECURITY AGENT {i}", "security-force", "Engineering", "CRITICAL", f"agents/security-force/agent-{str(i).zfill(3)}-security.md") for i in range(102, 108)],
    # RAG 108-113
    *[Agent(str(i).zfill(3), f"RAG AGENT {i}", "rag-knowledge", "Engineering", "HIGH", f"agents/rag-knowledge/agent-{str(i).zfill(3)}-rag.md") for i in range(108, 114)],
    # HRM 114-119
    *[Agent(str(i).zfill(3), f"HRM AGENT {i}", "hrm-workforce", "Operations", "HIGH", f"agents/hrm-workforce/agent-{str(i).zfill(3)}-hrm.md") for i in range(114, 120)],
]

def get_agent(agent_id: str) -> Optional[Agent]:
    return next((a for a in AGENT_REGISTRY if a.id == agent_id), None)

def get_committee(committee: str) -> list[Agent]:
    return [a for a in AGENT_REGISTRY if a.committee == committee]

def get_active_agents() -> list[Agent]:
    return [a for a in AGENT_REGISTRY if a.status == AgentStatus.ACTIVE]

def get_blocked_agents() -> list[Agent]:
    return [a for a in AGENT_REGISTRY if a.status == AgentStatus.BLOCKED]

if __name__ == "__main__":
    print(f"Total agents registered: {len(AGENT_REGISTRY)}")
    by_committee = {}
    for a in AGENT_REGISTRY:
        by_committee.setdefault(a.committee, 0)
        by_committee[a.committee] += 1
    for c, count in sorted(by_committee.items()):
        print(f"  {c}: {count} agents")
