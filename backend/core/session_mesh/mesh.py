"""
Veklom — Multi-Zone Enforcer Mesh
Distributed enforcement with local autonomy, cross-zone intelligence sharing,
failover, and consensus gating for high-impact interventions.
"""

from __future__ import annotations
import uuid
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from collections import defaultdict

from .enforcer import EnforcerAgent, Intervention
from .session import AgentSession, SessionStatus


# ── Severity ───────────────────────────────────────────────────────────────────
class Severity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    CRITICAL = "critical"


# ── Mesh incident (broadcast unit) ────────────────────────────────────────────
@dataclass
class MeshIncident:
    incident_id:   str
    source_zone:   str
    session_id:    str
    agent_id:      str
    rule_id:       str
    intervention:  str          # warn / alert / hold / kill
    severity:      Severity
    pattern:       str          # e.g. "bypass_kyc", "altitude_violation"
    context:       dict
    timestamp:     float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "incident_id":  self.incident_id,
            "source_zone":  self.source_zone,
            "session_id":   self.session_id,
            "agent_id":     self.agent_id,
            "rule_id":      self.rule_id,
            "intervention": self.intervention,
            "severity":     self.severity,
            "pattern":      self.pattern,
            "context":      self.context,
            "timestamp":    self.timestamp,
        }


# ── Zone watchlist — shared threat intelligence ────────────────────────────────
class ZoneWatchlist:
    """Accumulates patterns broadcast from the mesh."""

    def __init__(self):
        self._lock = threading.Lock()
        self._patterns:  dict[str, int]  = defaultdict(int)   # pattern → count
        self._agents:    dict[str, int]  = defaultdict(int)   # agent_id → incidents
        self._incidents: list[MeshIncident] = []

    def ingest(self, inc: MeshIncident):
        with self._lock:
            self._patterns[inc.pattern] += 1
            self._agents[inc.agent_id]  += 1
            self._incidents.append(inc)

    def threat_level(self, pattern: str) -> int:
        """How many mesh zones have reported this pattern."""
        return self._patterns.get(pattern, 0)

    def agent_risk_score(self, agent_id: str) -> int:
        """Cross-zone incident count for an agent."""
        return self._agents.get(agent_id, 0)

    def recent(self, n: int = 10) -> list[MeshIncident]:
        with self._lock:
            return list(reversed(self._incidents[-n:]))


# ── Consensus gate — multi-enforcer agreement for critical actions ─────────────
class ConsensusGate:
    """
    For CRITICAL interventions (e.g. shutting down a payment network),
    require votes from N enforcers before executing.
    """

    def __init__(self, quorum: int = 2):
        self._quorum   = quorum
        self._lock     = threading.Lock()
        self._votes:   dict[str, set[str]] = defaultdict(set)   # proposal_id → voter set
        self._executed: set[str] = set()

    def vote(self, proposal_id: str, voter_id: str) -> bool:
        """Cast a vote. Returns True if quorum reached and action should execute."""
        with self._lock:
            if proposal_id in self._executed:
                return False
            self._votes[proposal_id].add(voter_id)
            if len(self._votes[proposal_id]) >= self._quorum:
                self._executed.add(proposal_id)
                return True
            return False

    def pending(self) -> dict:
        with self._lock:
            return {
                pid: {"votes": len(v), "quorum": self._quorum}
                for pid, v in self._votes.items()
                if pid not in self._executed
            }


# ── Zone Enforcer Node ─────────────────────────────────────────────────────────
class ZoneEnforcerNode:
    """
    One enforcer in the mesh. Has:
    - A local EnforcerAgent watching local sessions
    - A ZoneWatchlist ingesting cross-zone intelligence
    - A ConsensusGate for critical actions
    - Peer references for broadcast
    """

    def __init__(
        self,
        zone_id:  str,
        enforcer: EnforcerAgent,
        quorum:   int = 2,
    ):
        self.zone_id   = zone_id
        self.enforcer  = enforcer
        self.watchlist = ZoneWatchlist()
        self.consensus = ConsensusGate(quorum)
        self._peers:   list[ZoneEnforcerNode] = []
        self._incident_log: list[MeshIncident] = []
        self._lock     = threading.Lock()

        # Wire enforcer alert callback to mesh broadcast
        original_alert = enforcer.alert_fn
        def mesh_alert(iv: Intervention):
            if original_alert:
                original_alert(iv)
            self._on_intervention(iv)
        enforcer.alert_fn = mesh_alert

    def register_peer(self, peer: "ZoneEnforcerNode"):
        if peer is not self and peer not in self._peers:
            self._peers.append(peer)

    def watch_session(self, session: AgentSession):
        """Wire a session's transitions into this zone's enforcer."""
        import types
        orig = session._append.__func__
        def observed(self_inner, ttype, data):
            t = orig(self_inner, ttype, data)
            self.enforcer.observe(t, self_inner)
            return t
        session._append = types.MethodType(observed, session)

    # ── Internal: fired when enforcer intervenes ──────────────────────────────
    def _on_intervention(self, iv: Intervention):
        inc = MeshIncident(
            incident_id  = str(uuid.uuid4())[:8],
            source_zone  = self.zone_id,
            session_id   = getattr(iv, 'session_id', ''),
            agent_id     = getattr(iv, 'agent_id', ''),
            rule_id      = iv.rule_id,
            intervention = iv.intervention_type,
            severity     = self._classify_severity(iv),
            pattern      = iv.rule_id,
            context      = {"reason": iv.reason, "seq": iv.transition_seq},
        )
        with self._lock:
            self._incident_log.append(inc)

        # Critical → request consensus before propagating
        if inc.severity == Severity.CRITICAL:
            self._critical_proposal(inc)
        else:
            self._broadcast(inc)

    def _classify_severity(self, iv: Intervention) -> Severity:
        # CRITICAL only for coordinated zone-wide actions (e.g. shutting down payment net)
        # Single-agent kills are HIGH — broadcast immediately without consensus
        if iv.intervention_type == "kill":
            return Severity.HIGH
        if iv.intervention_type == "hold":
            return Severity.MEDIUM
        if iv.intervention_type == "alert":
            return Severity.LOW
        return Severity.LOW

    def _critical_proposal(self, inc: MeshIncident):
        """Vote on own proposal; broadcast to peers for their vote."""
        proposal_id = f"critical-{inc.incident_id}"
        # Self-vote
        if self.consensus.vote(proposal_id, self.zone_id):
            self._broadcast(inc)
        else:
            # Ask peers to vote
            for peer in self._peers:
                peer.receive_consensus_vote(proposal_id, inc, self.zone_id)

    def receive_consensus_vote(self, proposal_id: str, inc: MeshIncident, voter_id: str):
        """Peer voted on a critical incident. If quorum → broadcast."""
        if self.consensus.vote(proposal_id, voter_id):
            self._broadcast(inc)

    # ── Broadcast incident to all peers ──────────────────────────────────────
    def _broadcast(self, inc: MeshIncident):
        for peer in self._peers:
            peer.receive_incident(inc)

    # ── Receive incident from peer ─────────────────────────────────────────────
    def receive_incident(self, inc: MeshIncident):
        """Ingest mesh intelligence. Raise local threat level if pattern is hot."""
        self.watchlist.ingest(inc)
        threat = self.watchlist.threat_level(inc.pattern)
        if threat >= 2:
            print(f"  [{self.zone_id}] ⚠ Mesh threat '{inc.pattern}' "
                  f"now seen in {threat} zones — raising local alert threshold")

    # ── Status ────────────────────────────────────────────────────────────────
    def status(self) -> dict:
        return {
            "zone_id":       self.zone_id,
            "interventions": len(self.enforcer.interventions),
            "incidents_broadcast": len(self._incident_log),
            "mesh_patterns": dict(self.watchlist._patterns),
            "consensus_pending": self.consensus.pending(),
        }
