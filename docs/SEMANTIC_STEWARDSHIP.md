# Veklom Sovereign Ecosystem — Semantic Stewardship & Datasets Guideline
## Inspired by "The Zwitterion Signal" (Zheng, Leito, & Green, MIT 2024)

> [!IMPORTANT]
> This document governs the naming taxonomy, column attributes, and schema representation of telemetry, SLA performance bonds (Micro-Stakes), and settlement ledgers across the entire Veklom Sovereign Network. All developers and autonomous agents must strictly adhere to these definitions.

---

## 1. Context: "The Zwitterion Signal"

In November 2024, researchers from MIT and the University of Tartu published a landmark study: *Widespread Misinterpretation of pKa Terminology for Zwitterionic Compounds and Its Consequences*. 

They uncovered a systematic error corrupting major biochemical repositories (such as the ChEMBL database). Because repositories aggregated literature using different naming conventions (specifically swapping "acidic" and "basic" labels for zwitterionic compounds based on different proton gain/loss conventions), numerical values were quietly swapped. 
*   **The Consequence**: Machine learning models trained on these flawed, ambiguously labeled datasets learned contradictory features, significantly degrading prediction accuracy for the very molecules most critical to drug discovery.

### The Signal for Veklom
Veklom operates a high-frequency, decentralized execution network where AI agents run complex jobs governed by real-time Micro-Stakes (VNP) and Settlement Ledgers (x402). If our telemetry, SLA performance markers, and settlement logs contain ambiguous, context-dependent, or shorthand labels, **we will systematically corrupt our own agent-training and scoring models**.

---

## 2. Core Stewardship Principles

To prevent semantic drift and ensure our ledger records are clean, unambiguous, and structurally stable, we enforce the following rules:

### Rule 1: No Amorphous Columns or Shorthand Labels
Do **NOT** use ambiguous shorthand column names like `high_val`, `low_val`, `rate_type`, or standard/generic labels that change meaning depending on context.
*   **Bad**: `latency_score: float` or `stake_yield: float`
*   **Good**: `sla_deviation_percent: float`, `effective_p95_latency_ms: int`, `yield_payout_minor_usdc: int`

### Rule 2: Absolute Value Domain Explicitly Bound
Every numeric field representing a unit of measure (time, compute, currency, memory) must state its unit directly in the variable/column name or have a strictly typed domain.
*   **Time/Latency**: Must use `_ms` or `_sec` suffixes.
*   **Financials/USDC/SLA Stakes**: Must be recorded in minor units (e.g., `_minor_usdc` or `_atoms`) off the hot-path to avoid floating-point rounding errors and serialization drift.

### Rule 3: Bidirectional (Amphoteric) Schema Equivalence
Every tool registered inside the Veklom ecosystem must have an in-memory compiler definition that maps its Pydantic model directly to its OpenAPI structure and its MCP JSON Schema. There must be **zero manual conversion tables** or external translation gateways that could introduce schema drift.

---

## 3. Reference Implementation: Telemetry & VNP Ledger Schemas

Below is the standard layout for recording probe telemetry and performance slash events under strict semantic stewardship.

### VNP Telemetry Record
```json
{
  "api_id": "api_uuid_9831a2",
  "region_code": "us-east-1",
  "window_start": "2026-06-28T18:00:00Z",
  "window_end": "2026-06-28T19:00:00Z",
  "sample_count": 720,
  "success_count": 718,
  "p50_latency_ms": 112,
  "p95_latency_ms": 185,
  "p99_latency_ms": 310,
  "error_rate_percent": 0.27,
  "uptime_percent": 99.72,
  "sla_deviation_percent": 3.25
}
```

### SLA Performance Bond Ledger Entry (Slash Log)
```json
{
  "slash_id": "slsh_91238a87cd",
  "provider_id": "prov_871ab93",
  "epoch_index": 412,
  "sla_metric_checked": "p95_latency_ms",
  "sla_threshold_limit_ms": 150,
  "observed_value_ms": 185,
  "penalty_minor_usdc": 350000,
  "yield_slashed_atoms": 120500,
  "evidence_hash_sha256": "8f309a2be7a871cb1b93fcd..."
}
```

---

## 4. Compliance Checklists for Agents
When generating new migrations, database models, or API endpoints:
1.  **Audit for Ambiguity**: Can this field name be interpreted in two different ways by an LLM or an analytics pipeline? (If yes, rename it to be self-documenting).
2.  **Verify Serialization**: Ensure the schema depth does not exceed 6 nesting levels to prevent circular parsing locks.
3.  **Sanitize Exceptions**: Ensure any error paths logging these fields intercept SQLAlchemy traces and replace sensitive system directory strings (`/data/coolify/`, `C:\Users\`) with clean cryptographic verification signatures.
