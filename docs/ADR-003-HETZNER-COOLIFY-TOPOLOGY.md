# ADR-003: Hetzner Coolify Topology

## Status
Approved

## Context
Previous VNP deployment proposals relied on fictional deployments across AWS Lambda, EventBridge, GCP, Oracle Cloud, Northflank, Tokyo, or Helsinki. This led to fragmented infrastructure assumptions and unrealistic node representations. The actual physical infrastructure is entirely based on Hetzner servers managed by Coolify.

## Decision
The authoritative VNP physical measurement network and overarching Veklom backend infrastructure must exclusively target the existing Hetzner/Coolify environments. All other regional or cloud deployment documentation is archived as historical research and MUST NOT be implemented.

### Authoritative VNP Physical Nodes
The initial network consists of these 5 nodes:

| Server                     | Physical location                | Location code    | Provider | Deployment platform |
| -------------------------- | -------------------------------- | ---------------- | -------- | ------------------- |
| `veklom-edge-us-east`      | Ashburn, Virginia, United States | `us-ashburn`     | Hetzner  | Coolify             |
| `veklom-prod-1`            | Hillsboro, Oregon, United States | `us-hillsboro`   | Hetzner  | Coolify             |
| `veklom-edge-eu-north2`    | Nuremberg, Germany               | `de-nuremberg`   | Hetzner  | Coolify             |
| `veklom-edge-eu-central`   | Falkenstein, Germany             | `de-falkenstein` | Hetzner  | Coolify             |
| `veklom-edge-ap-southeast` | Singapore                        | `sg-singapore`   | Hetzner  | Coolify             |

### Infrastructure Rules
1. **No Fictional Clouds:** Do not create or infer AWS, GCP, Oracle, Lambda, or fictional regions (e.g. Tokyo). 
2. **No AWS Identifiers:** AWS-style identifiers (`us-east-1`) are prohibited. Use the canonical Location Code.
3. **Cryptographic Identity:** A physical server hostname is not the node identity. Every VNP probe receives a stable UUID and a registered Ed25519 key. Private keys remain node-side and are NEVER copied to the central registry.
4. **Node Registry Fields:** The registry must separately store: node UUID, host reference, location code, physical city/country, jurisdiction, provider, platform, Coolify application reference, image digest, software version, key ID, key status, last heartbeat, and health state.
5. **Liveness Criteria:** A Hetzner server is NOT automatically a Live VNP node. It becomes Live only after successful registration, verified signing key, fresh heartbeat, deployed probe software, at least one accepted real observation, and satisfied freshness criteria.
6. **Frontend Derivation:** The frontend derives topology EXCLUSIVELY from the canonical registry. No hardcoded frontend topology is permitted. Unregistered/stale nodes show as Disconnected or Config Incomplete.
7. **Agent Representation:** Amphoteric agents (logical participants) must never be represented as physical measurement locations.

## Consequences
- The VNP topology is strictly bound to 5 physical Hetzner servers.
- Any attempt to use simulated pools or synthetic measurements will be rejected by the VNP state compiler.
