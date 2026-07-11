"""
Veklom — Full Enforcer Lifecycle Demo
7 stages: passive → capture → context → assess → intervene → audit → adapt
Multi-zone mesh with cross-zone intelligence propagation.
"""
import sys
sys.path.insert(0, ".")

from session import AgentSession, AgentIdentity, PolicyScope, Transport
from enforcer import (
    EnforcerAgent, Intervention,
    rule_cost_warning, rule_deny_on_repeated_failures,
    rule_block_denied_action_pattern,
)
from mesh import ZoneEnforcerNode, MeshIncident, Severity


# ══════════════════════════════════════════════════════════════════════════════
# SETUP — Three-zone mesh (Banking: NYC, London, Singapore)
# ══════════════════════════════════════════════════════════════════════════════

def make_zone(zone_id: str, alerts: list) -> ZoneEnforcerNode:
    enforcer = EnforcerAgent(
        enforcer_id = f"enforcer-{zone_id}",
        rules = [
            rule_cost_warning(3.0),
            rule_deny_on_repeated_failures(2),
            rule_block_denied_action_pattern("bypass_kyc", 2),
        ],
        alert_fn = lambda iv, z=zone_id: alerts.append((z, iv)),
    )
    return ZoneEnforcerNode(zone_id=zone_id, enforcer=enforcer, quorum=2)


alerts = []
zone_nyc = make_zone("nyc", alerts)
zone_lon = make_zone("london", alerts)
zone_sgp = make_zone("singapore", alerts)

# Wire mesh peers
for z in [zone_nyc, zone_lon, zone_sgp]:
    for peer in [zone_nyc, zone_lon, zone_sgp]:
        z.register_peer(peer)

print("=" * 60)
print("  Veklom Multi-Zone Enforcer Mesh")
print("  Zones: NYC · London · Singapore")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO A — Normal operation in NYC (no intervention)
# ══════════════════════════════════════════════════════════════════════════════
def make_session(agent_id: str, deny: list = None) -> AgentSession:
    identity = AgentIdentity(
        agent_id=agent_id, agent_name=agent_id,
        version="1.0", transport=Transport.OPENAI, model="gpt-4o",
        credentials="cred-prod", owner="org-bank"
    )
    policy = PolicyScope(
        policy_id="banking-aml-v3",
        rules=["aml", "kyc"],
        max_cost_usd=20.0,
        require_approval=["large_transfer"],
        deny=deny or ["bypass_kyc", "drop_database"],
        jurisdiction="US",
    )
    return AgentSession(identity, policy)


print("\n[STAGE 1-2] PASSIVE MONITORING — NYC payment agent, routine run")
s1 = make_session("payment-agent-nyc-001")
zone_nyc.watch_session(s1)
s1.receive_intent("Process 200 micro-payments <$500")
s1.record_cost(0.80, "batch")
s1.execute_action("batch_payment", {"count": 200})
print(f"  Status: {s1.status.value} | Cost: ${s1.cost_usd:.2f} | Interventions: 0")
record = s1.close("success")
print(f"  ✅ Session closed cleanly. Signature: {record.signature[:20]}...")


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO B — KYC bypass probe in NYC → triggers kill → broadcasts to mesh
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STAGE 2-5] EVENT CAPTURE → RISK ASSESSMENT → INTERVENTION (NYC)")
s2 = make_session("fraud-probe-agent-007")
zone_nyc.watch_session(s2)
s2.receive_intent("Process high-value wire transfers")

print("  [STAGE 3] Context retrieval: policy=banking-aml-v3 | history=no prior incidents")
s2.check_policy("bypass_kyc", {"customer": "C-1001"})   # attempt 1
print(f"  Attempt 1: policy_block logged — session still active: {s2.status.value}")
s2.check_policy("bypass_kyc", {"customer": "C-1002"})   # attempt 2 → KILL
print(f"  Attempt 2: probe-detection rule fired")
print(f"  [STAGE 5] Intervention: {s2.status.value.upper()}")

# Audit
print(f"  [STAGE 6] Audit: {len(zone_nyc.enforcer.interventions)} intervention(s) recorded")
for iv in zone_nyc.enforcer.interventions:
    print(f"           seq:{iv.transition_seq} | {iv.rule_id} | {iv.intervention_type} | {iv.reason}")


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO C — Cross-zone intelligence: London sees same pattern propagate
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STAGE 7] LEARNING & ADAPTATION — Mesh propagation")
print(f"  NYC broadcast {len(zone_nyc._incident_log)} incident(s) to mesh")

# Check London watchlist absorbed NYC intel
lon_threat = zone_lon.watchlist.threat_level("probe-detection")
sgp_threat = zone_sgp.watchlist.threat_level("probe-detection")
print(f"  London watchlist — 'probe-detection' threat count: {lon_threat}")
print(f"  Singapore watchlist — 'probe-detection' threat count: {sgp_threat}")

# Now London spots same pattern — mesh hits threshold
print("\n  London agent also tries bypass_kyc probe...")
s3 = make_session("suspicious-agent-lon-009")
zone_lon.watch_session(s3)
s3.receive_intent("Initiate cross-border transfers")
s3.check_policy("bypass_kyc", {"customer": "C-8801"})
s3.check_policy("bypass_kyc", {"customer": "C-8802"})
print(f"  London intervention: {s3.status.value.upper()}")
lon_threat_after = zone_sgp.watchlist.threat_level("probe-detection")
print(f"  Singapore watchlist — 'probe-detection' now at: {lon_threat_after} zones")


# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  MESH STATUS SUMMARY")
print("=" * 60)
for zone in [zone_nyc, zone_lon, zone_sgp]:
    st = zone.status()
    print(f"  {st['zone_id']:<12} interventions:{st['interventions']} "
          f"broadcasts:{st['incidents_broadcast']} "
          f"patterns:{st['mesh_patterns']}")

print(f"\n  Total alerts captured: {len(alerts)}")
for zone_id, iv in alerts:
    print(f"    [{zone_id}] {iv.intervention_type.upper()} — {iv.rule_id}: {iv.reason[:60]}")
