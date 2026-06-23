# Veklom Runtime Authority

This repository is governed by the **Veklom Runtime Authority**.

All Agents MUST adhere to the following vocabulary and anti-patterns:

## Vocabulary
* **Micro-Stakes (VNP)**: Real-time SLA performance bonds (`X-VNP-Stake`, `yield`, `slashed`). Always write to `vnp_stake_logs` off the hot-path.
* **Settlement Ledger (x402)**: Cryptographic proof of paid compute (`X-Veklom-Receipt-ID`, `evidence_hash`).
* **IdentityRAG (PGL)**: Cross-cluster tenant resolution mapping `sub` claims to `workspace_id`.
* **Zero-Trust Middleware**: Default-deny gateways ensuring continuous authorization.

## Anti-Patterns (Slop)
* **DO NOT** hardcode Stripe links (e.g. `res.redirect("stripe.com")`). Always use `_build_402_response("insufficient_funds")`.
* **DO NOT** use ephemeral accounting like `console.log("SLA missed")`. Always persist to the VNP Ledger off the hot-path.
* **DO NOT** trust client payloads for tenant identity (`req.body.tenant_id`). Always extract `workspace_id` from the signed JWT via the PGL IdentityRAG mechanism.

