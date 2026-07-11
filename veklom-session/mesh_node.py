"""
Veklom — Global Enforcer Mesh Node (FastAPI + WebSocket)

Each zone runs this server. Zones connect to each other as WebSocket peers.
When an enforcer fires, the incident is signed, broadcast to all peers,
and written to the global audit ledger.

Architecture per node:
  - POST /sessions/*              — local session control plane
  - WS   /mesh/connect            — peer-to-peer mesh channel
  - POST /mesh/peers              — register a peer endpoint
  - GET  /mesh/ledger             — global federated audit ledger
  - GET  /mesh/watchlist          — active threat intelligence
  - POST /mesh/consensus/vote     — cast a vote on a critical proposal
"""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional
import types

# Configure logger
logger = logging.getLogger("veklom.mesh_node")

# Ensure the backend root is on python path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.core.database.database import get_db_session
    from backend.db.models.session_mesh import (
        VeklomAgentSession,
        VeklomSessionTransition,
        VeklomMeshIncident,
        VeklomLedgerEntry
    )
except ImportError:
    # Safe fallback if run completely stand-alone
    get_db_session = None
    VeklomAgentSession = None
    VeklomSessionTransition = None
    VeklomMeshIncident = None
    VeklomLedgerEntry = None

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from session import AgentSession, AgentIdentity, PolicyScope, Transport, SessionStatus
from enforcer import EnforcerAgent, Intervention, rule_cost_warning, rule_deny_on_repeated_failures, rule_block_denied_action_pattern
from mesh import ZoneEnforcerNode, MeshIncident, Severity, ZoneWatchlist, ConsensusGate


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNED INCIDENT ENVELOPE (Ed25519 ASYMMETRIC UPGRADE)
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from crypto import ZoneKeyPair, MeshKeyRegistry, sign_incident_ed25519, verify_incident_ed25519
except ImportError:
    from .crypto import ZoneKeyPair, MeshKeyRegistry, sign_incident_ed25519, verify_incident_ed25519

_default_keypair = ZoneKeyPair()
_default_registry = MeshKeyRegistry()
_default_registry.register("nyc", _default_keypair.public_hex())
_default_registry.register("london", _default_keypair.public_hex())
_default_registry.register("singapore", _default_keypair.public_hex())
_default_registry.register("zone-a-nyc", _default_keypair.public_hex())
_default_registry.register("zone-b-lon", _default_keypair.public_hex())
_default_registry.register("zone-c-sgp", _default_keypair.public_hex())


def sign_incident(inc: MeshIncident, keypair: Optional[ZoneKeyPair] = None) -> str:
    kp = keypair or _default_keypair
    inc_dict = inc.to_dict()
    signed_dict = sign_incident_ed25519(inc_dict, kp)
    return signed_dict["signature"]


def verify_incident(inc: MeshIncident, signature: str, registry: Optional[MeshKeyRegistry] = None) -> bool:
    reg = registry or _default_registry
    inc_dict = inc.to_dict()
    inc_dict["signature"] = signature
    return verify_incident_ed25519(inc_dict, reg)


@dataclass
class SignedIncidentEnvelope:
    incident:  MeshIncident
    signature: str
    sender_zone: str
    public_key: Optional[str] = None

    def to_wire(self) -> str:
        return json.dumps({
            "incident":    self.incident.to_dict(),
            "signature":   self.signature,
            "sender_zone": self.sender_zone,
            "public_key":  self.public_key,
        })

    @staticmethod
    def from_wire(raw: str) -> "SignedIncidentEnvelope":
        d = json.loads(raw)
        inc_d = d["incident"]
        inc = MeshIncident(
            incident_id  = inc_d["incident_id"],
            source_zone  = inc_d["source_zone"],
            session_id   = inc_d["session_id"],
            agent_id     = inc_d["agent_id"],
            rule_id      = inc_d["rule_id"],
            intervention = inc_d["intervention"],
            severity     = inc_d["severity"],
            pattern      = inc_d["pattern"],
            context      = inc_d["context"],
            timestamp    = inc_d["timestamp"],
        )
        return SignedIncidentEnvelope(
            incident=inc,
            signature=d["signature"],
            sender_zone=d["sender_zone"],
            public_key=d.get("public_key"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FEDERATED AUDIT LEDGER  (append-only, chained)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LedgerEntry:
    seq:         int
    incident_id: str
    source_zone: str
    agent_id:    str
    pattern:     str
    severity:    str
    action:      str
    timestamp:   float
    prev_hash:   str
    entry_hash:  str

    def to_dict(self) -> dict:
        return asdict(self)


class FederatedAuditLedger:
    """
    Append-only chained ledger.
    Each entry hashes its content + previous entry hash → tamper-evident chain.
    """

    def __init__(self):
        self._entries: list[LedgerEntry] = []
        self._seen:    set[str] = set()

    def append(self, inc: MeshIncident) -> LedgerEntry:
        if inc.incident_id in self._seen:
            return None  # deduplicate cross-zone rebroadcasts
        self._seen.add(inc.incident_id)

        prev_hash = self._entries[-1].entry_hash if self._entries else "genesis"
        payload = f"{inc.incident_id}:{inc.agent_id}:{inc.pattern}:{inc.timestamp}:{prev_hash}"
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()

        entry = LedgerEntry(
            seq         = len(self._entries),
            incident_id = inc.incident_id,
            source_zone = inc.source_zone,
            agent_id    = inc.agent_id,
            pattern     = inc.pattern,
            severity    = inc.severity,
            action      = inc.intervention,
            timestamp   = inc.timestamp,
            prev_hash   = prev_hash,
            entry_hash  = entry_hash,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        for i, e in enumerate(self._entries):
            expected_prev = self._entries[i-1].entry_hash if i > 0 else "genesis"
            if e.prev_hash != expected_prev:
                return False
            payload = f"{e.incident_id}:{e.agent_id}:{e.pattern}:{e.timestamp}:{e.prev_hash}"
            if e.entry_hash != hashlib.sha256(payload.encode()).hexdigest():
                return False
        return True

    def all(self) -> list[dict]:
        return [e.to_dict() for e in self._entries]


# ═══════════════════════════════════════════════════════════════════════════════
# MESH NODE APP
# ═══════════════════════════════════════════════════════════════════════════════

def create_mesh_node(zone_id: str, quorum: int = 2) -> FastAPI:
    app = FastAPI(title=f"Veklom Mesh Node — {zone_id}", version="0.1.0")

    # Dynamic Keys
    node_keypair = ZoneKeyPair()
    registry = MeshKeyRegistry()
    registry.register(zone_id, node_keypair.public_hex())

    # State
    _sessions:    dict[str, AgentSession]   = {}
    _enforcers:   dict[str, EnforcerAgent]  = {}
    _zone_node:   ZoneEnforcerNode = ZoneEnforcerNode(
        zone_id  = zone_id,
        enforcer = EnforcerAgent(
            enforcer_id = f"zone-enforcer-{zone_id}",
            rules = [
                rule_cost_warning(3.0),
                rule_deny_on_repeated_failures(2),
                rule_block_denied_action_pattern("bypass_kyc", 2),
            ],
        ),
        quorum = quorum,
    )
    _ledger:      FederatedAuditLedger = FederatedAuditLedger()
    _ws_peers:    list[WebSocket]      = []  # active WebSocket connections to peers
    _peer_urls:   list[str]            = []  # registered peer URLs

    # ── Database Helpers ────────────────────────────────────────────────────
    async def _save_transition_to_db(session_id: str, t: Transition, status: str, cost: float):
        if not get_db_session:
            return
        try:
            from sqlalchemy import select
            async with get_db_session() as db:
                # 1. Update session status & cost in DB
                stmt = select(VeklomAgentSession).where(VeklomAgentSession.session_id == session_id)
                db_session = (await db.execute(stmt)).scalar_one_or_none()
                if db_session:
                    db_session.status = status
                    db_session.cost_usd = cost
                
                # 2. Check if transition already exists in DB
                stmt_t = select(VeklomSessionTransition).where(
                    VeklomSessionTransition.session_id == session_id,
                    VeklomSessionTransition.seq == t.seq
                )
                existing_t = (await db.execute(stmt_t)).scalar_one_or_none()
                if existing_t:
                    await db.commit()
                    return

                # Compute signature
                signing_key = "dev-key-replace-in-prod"
                entry_hash = t.compute_hash()
                sig = hmac.new(signing_key.encode(), entry_hash.encode(), hashlib.sha256).hexdigest()

                allowed = False if (t.type.value == "action.denied" or t.data.get("allowed") is False) else True

                db_transition = VeklomSessionTransition(
                    session_id=session_id,
                    seq=t.seq,
                    timestamp=t.timestamp,
                    action_type=t.type.value,
                    action_data=t.data,
                    allowed=allowed,
                    new_status=status,
                    prev_hash=t.prev_hash,
                    entry_hash=entry_hash,
                    signature=sig
                )
                db.add(db_transition)
                await db.commit()
        except Exception as exc:
            logger.error(f"Error saving transition to DB: {exc}")

    async def _save_incident_and_ledger_to_db(inc: MeshIncident, envelope_signature: str):
        if not get_db_session:
            return
        try:
            from sqlalchemy import select
            async with get_db_session() as db:
                # 1. Deduplicate check
                stmt = select(VeklomMeshIncident).where(VeklomMeshIncident.incident_id == inc.incident_id)
                existing_inc = (await db.execute(stmt)).scalar_one_or_none()
                if existing_inc:
                    return

                # 2. Save incident
                db_inc = VeklomMeshIncident(
                    incident_id=inc.incident_id,
                    source_zone=inc.source_zone,
                    session_id=inc.session_id,
                    agent_id=inc.agent_id,
                    rule_id=inc.rule_id,
                    intervention=inc.intervention,
                    severity=inc.severity,
                    pattern=inc.pattern,
                    context=inc.context,
                    timestamp=inc.timestamp,
                    signature=envelope_signature
                )
                db.add(db_inc)

                # 3. Save to Ledger Entry (chained)
                stmt_ledger = select(VeklomLedgerEntry).order_by(VeklomLedgerEntry.seq.desc()).limit(1)
                last_entry = (await db.execute(stmt_ledger)).scalar_one_or_none()
                
                prev_hash = last_entry.entry_hash if last_entry else "genesis"
                next_seq = (last_entry.seq + 1) if last_entry else 0
                
                payload = f"{inc.incident_id}:{inc.agent_id}:{inc.pattern}:{inc.timestamp}:{prev_hash}"
                entry_hash = hashlib.sha256(payload.encode()).hexdigest()

                db_ledger = VeklomLedgerEntry(
                    seq=next_seq,
                    incident_id=inc.incident_id,
                    source_zone=inc.source_zone,
                    agent_id=inc.agent_id,
                    pattern=inc.pattern,
                    severity=inc.severity,
                    action=inc.intervention,
                    timestamp=inc.timestamp,
                    prev_hash=prev_hash,
                    entry_hash=entry_hash
                )
                db.add(db_ledger)
                await db.commit()
        except Exception as exc:
            logger.error(f"Error saving incident/ledger to DB: {exc}")

    # Wire zone node → ledger
    original_broadcast = _zone_node._broadcast
    def ledger_broadcast(inc: MeshIncident):
        _ledger.append(inc)
        original_broadcast(inc)
        # Sign with actual dynamic keypair
        signature = sign_incident(inc, node_keypair)
        envelope = SignedIncidentEnvelope(inc, signature, zone_id, node_keypair.public_hex())
        asyncio.create_task(_ws_broadcast(envelope))
        # Persist our own broadcasted incident to DB
        asyncio.create_task(_save_incident_and_ledger_to_db(inc, signature))
    _zone_node._broadcast = ledger_broadcast

    # Wrap session watcher to intercept session._append
    original_watch_session = _zone_node.watch_session
    def db_watch_session(session: AgentSession):
        original_watch_session(session)
        orig_observed = session._append
        def db_observed(ttype, data):
            t = orig_observed(ttype, data)
            asyncio.create_task(_save_transition_to_db(session.session_id, t, session.status, session.cost_usd))
            return t
        session._append = db_observed
    _zone_node.watch_session = db_watch_session

    async def _ws_broadcast(envelope: SignedIncidentEnvelope):
        wire = envelope.to_wire()
        dead = []
        for ws in _ws_peers:
            try:
                await ws.send_text(wire)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_peers.remove(ws)

    # ── WebSocket: peer connection ──────────────────────────────────────────
    @app.websocket("/mesh/connect")
    async def mesh_ws_endpoint(ws: WebSocket):
        await ws.accept()
        _ws_peers.append(ws)
        try:
            while True:
                raw = await ws.receive_text()
                envelope = SignedIncidentEnvelope.from_wire(raw)
                if envelope.public_key:
                    # Dynamic auto-registration of peer's public key
                    registry.register(envelope.sender_zone, envelope.public_key)
                if not verify_incident(envelope.incident, envelope.signature, registry):
                    await ws.send_text(json.dumps({"error": "invalid_signature"}))
                    continue
                _zone_node.receive_incident(envelope.incident)
                _ledger.append(envelope.incident)
                # Persist received incident to Postgres DB asynchronously
                asyncio.create_task(_save_incident_and_ledger_to_db(envelope.incident, envelope.signature))
        except WebSocketDisconnect:
            _ws_peers.remove(ws)

    # ── Peer registration ───────────────────────────────────────────────────
    class PeerRequest(BaseModel):
        peer_url: str

    @app.post("/mesh/peers")
    def register_peer(req: PeerRequest):
        if req.peer_url not in _peer_urls:
            _peer_urls.append(req.peer_url)
        return {"peers": _peer_urls}

    @app.get("/mesh/peers")
    def list_peers():
        return {"zone_id": zone_id, "peers": _peer_urls, "ws_connections": len(_ws_peers)}

    # ── Global audit ledger ─────────────────────────────────────────────────
    @app.get("/mesh/ledger")
    async def get_ledger():
        if get_db_session:
            try:
                from sqlalchemy import select
                async with get_db_session() as db:
                    stmt = select(VeklomLedgerEntry).order_by(VeklomLedgerEntry.seq.asc())
                    db_entries = (await db.execute(stmt)).scalars().all()
                    
                    entries_list = []
                    chain_valid = True
                    for i, e in enumerate(db_entries):
                        expected_prev = "genesis" if i == 0 else db_entries[i-1].entry_hash
                        if e.prev_hash != expected_prev:
                            chain_valid = False
                        
                        payload = f"{e.incident_id}:{e.agent_id}:{e.pattern}:{e.timestamp}:{e.prev_hash}"
                        if e.entry_hash != hashlib.sha256(payload.encode()).hexdigest():
                            chain_valid = False
                            
                        entries_list.append({
                            "seq": e.seq,
                            "incident_id": e.incident_id,
                            "source_zone": e.source_zone,
                            "agent_id": e.agent_id,
                            "pattern": e.pattern,
                            "severity": e.severity,
                            "action": e.action,
                            "timestamp": e.timestamp,
                            "prev_hash": e.prev_hash,
                            "entry_hash": e.entry_hash
                        })
                        
                    return {
                        "zone_id": zone_id,
                        "entries": entries_list,
                        "chain_valid": chain_valid,
                        "count": len(entries_list)
                    }
            except Exception as e:
                logger.error(f"Error loading ledger from DB: {e}")
                
        # Fallback to in-memory
        return {
            "zone_id":     zone_id,
            "entries":     _ledger.all(),
            "chain_valid": _ledger.verify_chain(),
            "count":       len(_ledger.all()),
        }

    # ── Watchlist ───────────────────────────────────────────────────────────
    @app.get("/mesh/watchlist")
    async def get_watchlist():
        if get_db_session:
            try:
                from sqlalchemy import select
                async with get_db_session() as db:
                    stmt = select(VeklomMeshIncident).order_by(VeklomMeshIncident.timestamp.desc()).limit(20)
                    db_incidents = (await db.execute(stmt)).scalars().all()
                    
                    patterns = {}
                    agents = {}
                    
                    stmt_all = select(VeklomMeshIncident.pattern, VeklomMeshIncident.agent_id)
                    all_rows = (await db.execute(stmt_all)).all()
                    for p, aid in all_rows:
                        patterns[p] = patterns.get(p, 0) + 1
                        agents[aid] = agents.get(aid, 0) + 1
                        
                    recent_list = []
                    for i in db_incidents:
                        recent_list.append({
                            "incident_id": i.incident_id,
                            "source_zone": i.source_zone,
                            "session_id": i.session_id,
                            "agent_id": i.agent_id,
                            "rule_id": i.rule_id,
                            "intervention": i.intervention,
                            "severity": i.severity,
                            "pattern": i.pattern,
                            "context": i.context,
                            "timestamp": i.timestamp
                        })
                        
                    return {
                        "zone_id": zone_id,
                        "patterns": patterns,
                        "agents": agents,
                        "recent": recent_list
                    }
            except Exception as e:
                logger.error(f"Error loading watchlist from DB: {e}")

        wl = _zone_node.watchlist
        return {
            "zone_id":  zone_id,
            "patterns": dict(wl._patterns),
            "agents":   dict(wl._agents),
            "recent":   [i.to_dict() for i in wl.recent(20)],
        }

    # ── Consensus ───────────────────────────────────────────────────────────
    class VoteRequest(BaseModel):
        proposal_id: str
        voter_zone:  str

    @app.post("/mesh/consensus/vote")
    def vote(req: VoteRequest):
        executed = _zone_node.consensus.vote(req.proposal_id, req.voter_zone)
        return {
            "proposal_id": req.proposal_id,
            "quorum_reached": executed,
            "pending": _zone_node.consensus.pending(),
        }

    @app.get("/mesh/consensus")
    def get_consensus():
        return {
            "zone_id": zone_id,
            "pending": _zone_node.consensus.pending(),
            "quorum":  quorum,
        }

    # ── Session endpoints (mirror main.py but zone-aware) ───────────────────
    class OpenSessionRequest(BaseModel):
        agent_id:         str
        agent_name:       str
        model:            str
        transport:        str = "openai"
        credentials_ref:  str
        owner:            str
        policy_id:        str
        rules:            list[str] = []
        max_cost_usd:     float = 10.0
        require_approval: list[str] = []
        deny:             list[str] = []
        jurisdiction:     str = "GLOBAL"

    @app.post("/sessions", status_code=201)
    async def open_session(req: OpenSessionRequest):
        identity = AgentIdentity(
            agent_id=req.agent_id, agent_name=req.agent_name,
            version="1.0", transport=Transport(req.transport),
            model=req.model, credentials=req.credentials_ref, owner=req.owner,
        )
        policy = PolicyScope(
            policy_id=req.policy_id, rules=req.rules,
            max_cost_usd=req.max_cost_usd, require_approval=req.require_approval,
            deny=req.deny, jurisdiction=req.jurisdiction,
        )
        session = AgentSession(identity, policy)

        # 1. Create VeklomAgentSession in DB
        if get_db_session:
            try:
                async with get_db_session() as db:
                    db_sess = VeklomAgentSession(
                        session_id=session.session_id,
                        workspace_id=session.identity.owner,
                        agent_id=session.identity.agent_id,
                        agent_name=session.identity.agent_name,
                        model=session.identity.model,
                        transport=session.identity.transport.value,
                        credentials_ref=session.identity.credentials,
                        owner=session.identity.owner,
                        policy_id=session.policy.policy_id,
                        status=session.status,
                        cost_usd=session.cost_usd,
                        max_cost_usd=session.policy.max_cost_usd,
                        rules=session.policy.rules,
                        require_approval=session.policy.require_approval,
                        deny=session.policy.deny,
                        jurisdiction=session.policy.jurisdiction
                    )
                    db.add(db_sess)
                    await db.commit()
            except Exception as e:
                logger.error(f"Error saving session to DB: {e}")

        # 2. Watch session
        _zone_node.watch_session(session)
        _sessions[session.session_id] = session

        # 3. Save the initial SESSION_OPEN transition to DB manually
        if session.transitions:
            asyncio.create_task(_save_transition_to_db(session.session_id, session.transitions[0], session.status, session.cost_usd))

        return {"session_id": session.session_id, "zone": zone_id, "status": session.status}

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        s = _sessions.get(session_id)
        if s:
            return {"session_id": s.session_id, "status": s.status,
                    "cost_usd": s.cost_usd, "zone": zone_id,
                    "chain_intact": s.verify_chain()}

        if get_db_session:
            try:
                from sqlalchemy import select
                async with get_db_session() as db:
                    stmt = select(VeklomAgentSession).where(VeklomAgentSession.session_id == session_id)
                    db_sess = (await db.execute(stmt)).scalar_one_or_none()
                    if db_sess:
                        stmt_transitions = select(VeklomSessionTransition).where(
                            VeklomSessionTransition.session_id == session_id
                        ).order_by(VeklomSessionTransition.seq.asc())
                        db_transitions = (await db.execute(stmt_transitions)).scalars().all()
                        
                        chain_intact = True
                        for i, t in enumerate(db_transitions):
                            expected_prev = "genesis" if i == 0 else db_transitions[i-1].entry_hash
                            if t.prev_hash != expected_prev:
                                chain_intact = False
                                break
                                
                        return {
                            "session_id": db_sess.session_id,
                            "status": db_sess.status,
                            "cost_usd": db_sess.cost_usd,
                            "zone": zone_id,
                            "chain_intact": chain_intact
                        }
            except Exception as e:
                logger.error(f"Error querying session fallback: {e}")

        raise HTTPException(404, "Not found")

    class PolicyCheckRequest(BaseModel):
        action_type: str
        action_data: dict = {}

    @app.post("/sessions/{session_id}/policy-check")
    def policy_check(session_id: str, req: PolicyCheckRequest):
        s = _sessions.get(session_id)
        if not s:
            raise HTTPException(404, "Not found")
        if s.status != SessionStatus.ACTIVE:
            raise HTTPException(409, f"Session {s.status}")
        allowed = s.check_policy(req.action_type, req.action_data)
        return {"allowed": allowed, "status": s.status, "zone": zone_id}

    class KillRequest(BaseModel):
        reason: str = "kill switch"

    @app.post("/sessions/{session_id}/kill")
    async def kill_session(session_id: str, req: KillRequest):
        s = _sessions.get(session_id)
        record = None
        if s:
            record = s.kill(req.reason)

        if get_db_session:
            try:
                from sqlalchemy import select
                async with get_db_session() as db:
                    stmt = select(VeklomAgentSession).where(VeklomAgentSession.session_id == session_id)
                    db_sess = (await db.execute(stmt)).scalar_one_or_none()
                    if db_sess:
                        db_sess.status = "killed"
                        await db.commit()
            except Exception as e:
                logger.error(f"Error killing session in DB: {e}")

        if s and record:
            return {"session_id": session_id, "status": "killed",
                    "signature": record.signature[:16] + "...", "zone": zone_id}
        elif get_db_session:
            return {"session_id": session_id, "status": "killed",
                    "signature": "db-fallback", "zone": zone_id}

        raise HTTPException(404, "Not found")

    @app.post("/kill-all")
    async def kill_all(reason: str = "global kill switch"):
        killed = []
        for sid, s in _sessions.items():
            if s.status == SessionStatus.ACTIVE:
                s.kill(reason)
                killed.append(sid)

        if get_db_session:
            try:
                from sqlalchemy import update
                async with get_db_session() as db:
                    stmt = update(VeklomAgentSession).where(VeklomAgentSession.status == "active").values(status="killed")
                    await db.execute(stmt)
                    await db.commit()
            except Exception as e:
                logger.error(f"Error executing kill-all in DB: {e}")

        return {"zone": zone_id, "killed": killed, "count": len(killed)}

    @app.get("/zone/status")
    async def zone_status():
        zs = _zone_node.status()
        sessions_active = sum(1 for s in _sessions.values() if s.status == SessionStatus.ACTIVE)
        ledger_count = len(_ledger.all())
        ledger_valid = _ledger.verify_chain()

        if get_db_session:
            try:
                from sqlalchemy import select, func
                async with get_db_session() as db:
                    stmt_sess = select(func.count()).select_from(VeklomAgentSession).where(VeklomAgentSession.status == "active")
                    sessions_active = (await db.execute(stmt_sess)).scalar() or 0
                    
                    stmt_ledg = select(func.count()).select_from(VeklomLedgerEntry)
                    ledger_count = (await db.execute(stmt_ledg)).scalar() or 0
                    
                    stmt_chain = select(VeklomLedgerEntry).order_by(VeklomLedgerEntry.seq.asc())
                    db_entries = (await db.execute(stmt_chain)).scalars().all()
                    ledger_valid = True
                    for i, e in enumerate(db_entries):
                        expected_prev = "genesis" if i == 0 else db_entries[i-1].entry_hash
                        if e.prev_hash != expected_prev:
                            ledger_valid = False
                            break
            except Exception as e:
                logger.error(f"Error loading zone status from DB: {e}")

        return {
            **zs,
            "sessions_active": sessions_active,
            "ledger_entries":  ledger_count,
            "ledger_valid":    ledger_valid,
            "ws_peers":        len(_ws_peers),
        }

    return app
