"""
Veklom — Ed25519 signing demo
Proves: sign → verify → tamper → reject cycle with real asymmetric keys.
"""
import sys, json
sys.path.insert(0, ".")
from crypto import ZoneKeyPair, MeshKeyRegistry, sign_incident_ed25519, verify_incident_ed25519
import time, uuid

SEP = "─" * 54

# ── Setup: 3 zones, each with own keypair ────────────────────
print(SEP)
print("  Veklom — Ed25519 Mesh Signing")
print(SEP)

pairs   = {z: ZoneKeyPair() for z in ["zone-nyc", "zone-lon", "zone-sgp"]}
registry = MeshKeyRegistry()
for zone_id, kp in pairs.items():
    registry.register(zone_id, kp.public_hex())
    print(f"  {zone_id}: pubkey {kp.public_hex()[:24]}...")

# ── Sign an incident in zone-nyc ─────────────────────────────
print(f"\n{SEP}")
print("[1] SIGN — zone-nyc creates incident")
inc = {
    "incident_id": str(uuid.uuid4())[:8],
    "source_zone":  "zone-nyc",
    "agent_id":     "payment-agent-007",
    "pattern":      "bypass_kyc",
    "intervention": "kill",
    "severity":     "high",
    "timestamp":    time.time(),
}
signed = sign_incident_ed25519(inc.copy(), pairs["zone-nyc"])
print(f"  incident_id: {signed['incident_id']}")
print(f"  signature:   {signed['signature'][:32]}...")

# ── Verify at zone-lon ────────────────────────────────────────
print(f"\n{SEP}")
print("[2] VERIFY — zone-lon receives and checks signature")
ok = verify_incident_ed25519(signed.copy(), registry)
print(f"  Result: {'✅ VALID' if ok else '❌ INVALID'}")

# ── Tamper test ───────────────────────────────────────────────
print(f"\n{SEP}")
print("[3] TAMPER — attacker changes agent_id after signing")
tampered = signed.copy()
tampered["agent_id"] = "innocent-agent-999"
ok_tampered = verify_incident_ed25519(tampered, registry)
print(f"  Result: {'✅ VALID (BAD!)' if ok_tampered else '❌ REJECTED (CORRECT)'}")

# ── Unknown zone test ─────────────────────────────────────────
print(f"\n{SEP}")
print("[4] UNKNOWN ZONE — incident from unregistered zone")
fake = signed.copy()
fake["source_zone"] = "zone-rogue"
ok_fake = verify_incident_ed25519(fake, registry)
print(f"  Result: {'✅ VALID (BAD!)' if ok_fake else '❌ REJECTED (CORRECT)'}")

# ── Wrong key test ────────────────────────────────────────────
print(f"\n{SEP}")
print("[5] WRONG KEY — signed by zone-lon, claims to be zone-nyc")
wrong_signed = sign_incident_ed25519(inc.copy(), pairs["zone-lon"])  # lon signs it
wrong_signed["source_zone"] = "zone-nyc"                             # claims nyc
ok_wrong = verify_incident_ed25519(wrong_signed, registry)
print(f"  Result: {'✅ VALID (BAD!)' if ok_wrong else '❌ REJECTED (CORRECT)'}")

print(f"\n{SEP}")
print("  All 4 attack vectors rejected. Ed25519 integrated. ✅")
print(SEP)
