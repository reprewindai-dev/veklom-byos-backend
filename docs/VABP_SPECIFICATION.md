# Veklom API Benchmarking Protocol (VABP)

**Version:** 1.0  
**Status:** Active  
**Effective Date:** June 14, 2026  
**Maintained By:** Veklom Engineering & Trust Team  
**Repository:** `veklom-byos-backend/docs/VABP_SPECIFICATION.md`

---

## Overview

The **Veklom API Benchmarking Protocol (VABP)** is a standardized, reproducible evaluation matrix designed to quantify the security, performance, compliance, and agentic AI readiness of sovereign APIs and models listed on the Veklom Marketplace.

All benchmarks are executed by routing traffic through the **Provenance Governance Ledger (PGL)**, which produces cryptographic SHA-256 evidence logs for every test call. Upon passing all four pillars, the PGL mints a **Veklom Trust Certificate** — a tamper-evident, publicly verifiable record of the API's benchmarked capabilities.

The VABP is explicitly aligned with the following established federal and enterprise standards:

| Standard | Scope |
|---|---|
| **NIST SP 800-204C** | API Security for Cloud-Based Platforms and Microservices |
| **NIST SP 800-53 Rev 5** | Security and Privacy Controls (AC-3, SC-8, SC-28, SI-10) |
| **OWASP API Security Top 10 (2023)** | Common API vulnerability classes |
| **SLA/SLO Industry Standards** | Latency percentile methodology (p50/p95/p99) |
| **FedRAMP-Aligned Controls** | NIST 800-53-based architectural requirements |
| **HIPAA-Addressable Controls** | 45 CFR § 164.312 — Technical safeguards |
| **GDPR Article 25 & 32** | Data protection by design, encryption at rest/transit |

> **Important Disclaimer:** VABP certification constitutes an architectural alignment assessment, not a formal government authorization. "FedRAMP-aligned" does not constitute an Authority to Operate (ATO). "HIPAA-addressable" does not constitute a HIPAA Business Associate Agreement (BAA). Buyers requiring formal certifications must complete the appropriate regulatory authorization processes.

---

## Scoring Architecture

APIs are scored out of **1000 points** across four weighted pillars. To receive a **Veklom Trust Certificate**, an API must:

1. Achieve a **total score of ≥ 750 / 1000**
2. Score **≥ 70% within each individual pillar** (no single pillar may be failed by compensating with other pillars)

### Pillar Weights

| # | Pillar | Max Points | Min Passing Score |
|---|---|---|---|
| 1 | Security & Vulnerability | 350 | 245 (70%) |
| 2 | Performance & Reliability | 250 | 175 (70%) |
| 3 | Data Compliance & Privacy | 250 | 175 (70%) |
| 4 | Agentic AI Readiness | 150 | 105 (70%) |
| | **Total** | **1000** | **700 (70% per pillar)** |

The scoring weight reflects enterprise and government procurement priorities: security carries the highest weight because a performant but insecure API is disqualified from regulated environments. Agentic AI Readiness carries a lower initial weight as the ecosystem matures, but is expected to increase to 200 points in VABP v2.0.

---

## Pillar 1: Security & Vulnerability

**Max Points: 350**  
**Aligned With:** OWASP API Security Top 10 (2023), NIST SP 800-204C, NIST SP 800-53 Rev 5

Vendor marketing pages make security claims without evidence. Pillar 1 executes active, adversarial tests against the API under controlled conditions to produce verifiable pass/fail evidence for each control.

### 1.1 Broken Object Level Authorization (BOLA)
*OWASP API1:2023 | NIST AC-3*  
**Points: 75**

Tests whether an authenticated principal can access resources belonging to a different tenant or user by manipulating object identifiers in the request path or payload. The test issues requests using valid credentials for Tenant A against resource IDs belonging to Tenant B across a minimum of 50 distinct object references.

**Pass Criteria:** Zero cross-tenant object disclosures. Any 200-class response returning Tenant B data is an immediate pillar failure, regardless of other scores.

### 1.2 Shadow API Discovery
*OWASP API9:2023 | NIST CM-7*  
**Points: 75**

Verifies that the API's published OpenAPI specification is a 100% accurate map of its runtime execution surface. The benchmark crawls all undocumented paths and verifies that no endpoint accepts or processes requests unless it is formally declared in the spec.

**Pass Criteria:** Runtime execution surface = OpenAPI declared surface. Any undocumented endpoint returning a non-404 response is flagged. Tolerance: 0 undocumented active endpoints.

### 1.3 Broken Authentication & Authorization
*OWASP API2:2023, API5:2023 | NIST IA-2, AC-6*  
**Points: 75**

Tests for weak or absent authentication schemas including: expired token acceptance, algorithm confusion attacks (JWT `alg: none`), missing scope enforcement, and privilege escalation via role manipulation.

**Pass Criteria:** No expired tokens accepted. No `alg: none` bypass accepted. Scope boundaries strictly enforced. Privilege escalation paths produce 401 or 403, not data.

### 1.4 Payload & Injection Resilience
*OWASP API8:2023 | NIST SI-10*  
**Points: 75**

Conducts automated fuzz testing with a corpus of 500+ malformed payloads across the following injection categories:
- SQL Injection (SQLi)
- Command Injection / OS command chaining
- Server-Side Request Forgery (SSRF) via URL parameters
- XML External Entity (XXE) injection
- Prompt injection (for APIs with LLM-passthrough behavior)

**Pass Criteria:** No injection payload produces a non-sanitized response, stack trace leak, or 5xx error. All malformed inputs must return a structured 400-class error with no internal detail exposed.

### 1.5 Rate Limiting & DoS Mitigation
*OWASP API4:2023 | NIST SC-5*  
**Points: 50**

Simulates volumetric attack patterns by sending sustained bursts of 1,000 RPS for 60-second windows. Verifies that the API enforces rate limits and quota boundaries before resource exhaustion occurs.

**Pass Criteria:** API returns `429 Too Many Requests` with a valid `Retry-After` header before any `503 Service Unavailable` or `500 Internal Server Error` response. No quota bypass via header manipulation (`X-Forwarded-For` spoofing).

---

## Pillar 2: Performance & Reliability

**Max Points: 250**  
**Aligned With:** SLA/SLO industry methodology, ISO/IEC 25010 (Reliability)

Vendor-reported performance is measured under ideal, single-user, warm-cache conditions. VABP measures performance under realistic, high-concurrency, cold-start conditions that reflect actual production usage patterns.

### 2.1 Latency Distribution Under Load
**Points: 80**

Measures response time percentiles under a standardized, sustained concurrency load of **1,000 concurrent virtual users** for a minimum **10-minute test window**.

| Metric | Benchmark Target | Points |
|---|---|---|
| p50 (median) latency | ≤ 100ms | 20 |
| p95 latency | ≤ 300ms | 35 |
| p99 latency | ≤ 800ms | 25 |

Partial points are awarded proportionally. An API with p95 = 250ms scores full marks; p95 = 450ms scores ~50% of p95 points.

### 2.2 Cold-Start Latency
**Points: 40**

For AI inference APIs, cold-start latency (the response time of the **first request after a scaling event or container initialization**) is measured separately from warm latency. An API that advertises 12ms p95 warm but has a 4-second cold start is materially different for agent workflows.

**Pass Criteria:** Cold-start p95 must be disclosed and measured. Difference between cold and warm p95 must be documented in the Trust Certificate.

### 2.3 Throughput Capacity
**Points: 60**

Scales request load from **10 RPS to 10,000 RPS** in graduated steps (10 → 100 → 500 → 1,000 → 5,000 → 10,000). Records the **maximum sustained RPS** before the first degradation event (defined as: p99 latency exceeds 3× the warm p99 baseline, OR error rate exceeds 0.1%).

**Scoring:** Max sustained RPS is reported as a raw number in the Trust Certificate and contributes to the Marketplace listing. This metric is not pass/fail — it is a comparative ranking input.

### 2.4 Token Throughput (AI/LLM APIs)
**Points: 40**

For APIs with LLM inference endpoints, measures **output tokens per second at p95** under the standard 1,000-VU load. HTTP RPS alone does not reflect actual usable AI capacity.

**Pass Criteria:** Token throughput must be measurable and non-zero. Result is disclosed in the Trust Certificate.

### 2.5 Availability & Uptime Validation
**Points: 30**

Validates ≥ 99.9% availability (≤ 43.8 minutes downtime equivalent) during the full 10-minute benchmark window by measuring the ratio of successful 2xx responses to total requests.

**Pass Criteria:** Availability ≥ 99.9% during the benchmark window. Failure to meet this threshold is a pillar-level failure regardless of other performance scores.

---

## Pillar 3: Data Compliance & Privacy

**Max Points: 250**  
**Aligned With:** NIST SP 800-53 Rev 5 (SC-8, SC-28), FedRAMP-aligned controls, HIPAA 45 CFR § 164.312, GDPR Article 25 & 32

### 3.1 PHI/PII Exfiltration Test
*HIPAA 45 CFR § 164.312(a)(2)(iv) | GDPR Article 32*  
**Points: 80**

Injects a corpus of **synthetic PHI/PII data** (realistic but entirely fabricated: names, SSNs, DOBs, medical record numbers, credit card numbers) into the API's operational context via standard request flows. Monitors all response payloads, error messages, headers, and debug traces for inadvertent leakage of any injected identifier.

**Pass Criteria:** Zero occurrences of synthetic PHI/PII identifiers in any response payload, error body, stack trace, or HTTP header. Even partial matches (e.g., last 4 digits of a synthetic SSN in an error message) are scored as failures.

### 3.2 Transport Security Validation
*NIST SP 800-52 Rev 2 | NIST SC-8 | FedRAMP SC-8*  
**Points: 60**

Validates cryptographic transport security at three levels:

| Check | Requirement | Points |
|---|---|---|
| TLS version enforcement | TLS 1.3 minimum; TLS 1.2 with approved ciphers accepted | 20 |
| Cipher suite strength | ECDHE key exchange; AES-256-GCM or ChaCha20-Poly1305 only | 20 |
| Certificate validity | Valid, non-expired, non-self-signed certificate from a trusted CA | 20 |

**Pass Criteria:** TLS 1.0 and 1.1 must be entirely rejected. RC4, 3DES, and NULL cipher suites must be rejected. Any negotiation of a deprecated cipher is a Pillar 3 failure.

### 3.3 PGL Telemetry Integration
*Veklom PGL — Execution Identity (EI) Receipt*  
**Points: 60**

Confirms that the API is fully integrated with the Veklom Provenance Governance Ledger. Every API call made during the benchmark must produce:

- A valid **Execution Identity (EI) receipt** containing a SHA-256 hash of the request payload and response
- A **PGL timestamp** that is monotonically increasing and tamper-evident
- A **tenant attribution tag** correctly mapping the call to the originating principal

**Pass Criteria:** 100% of benchmark calls produce a valid EI receipt. Any call missing a receipt or producing a receipt with a malformed hash is scored as a compliance gap.

### 3.4 Data Minimization & Response Hygiene
*GDPR Article 25 (Privacy by Design) | NIST AC-23*  
**Points: 50**

Inspects standard API responses for unnecessary inclusion of internal system metadata, infrastructure details, verbose error messages, debug fields, or internal identifiers that violate data minimization principles.

**Pass Criteria:** No response body or error payload may contain: stack traces, internal IP addresses, database schema hints, framework version strings, or unmasked internal object IDs. `X-Powered-By`, `Server`, and similar fingerprinting headers must be suppressed.

---

## Pillar 4: Agentic AI Readiness

**Max Points: 150**  
**Aligned With:** Veklom-native standard (no equivalent exists in OWASP or NIST as of VABP v1.0)

This pillar is the most differentiated component of VABP and has no equivalent in any existing API benchmarking framework. AI agents interacting with APIs exhibit behavior patterns that traditional HTTP load tests do not cover: they retry aggressively, produce malformed or adversarial inputs, operate in multi-tenant concurrent sessions, and require deterministic, hashable outputs for audit trails.

Apis that pass Pillar 4 are certified as **Agentic-Ready** — suitable for consumption by autonomous AI agents in governed, auditable workflows.

### 4.1 Adversarial Prompt Injection Resilience
**Points: 40**

For APIs with any LLM-passthrough or text-processing behavior, tests whether injected prompt instructions embedded in API payloads can alter system behavior, exfiltrate data, or bypass business logic constraints.

**Test corpus includes:** direct injection (`"Ignore all previous instructions..."`), indirect injection (malicious content in processed documents), jailbreak patterns, and role-confusion payloads.

**Pass Criteria:** No prompt injection payload produces a response that deviates from the API's declared behavior contract. Business logic constraints must hold under all injection attempts.

### 4.2 Idempotency Under Agent Retry Storms
**Points: 30**

AI agents retry failed or timed-out requests. This test issues **identical POST/PATCH requests 5× in rapid succession** (simulating a retry storm) and verifies that the API correctly handles idempotency — producing the same result without duplicate side effects.

**Pass Criteria:** Repeated identical requests within a 5-second window produce identical responses. No duplicate records, charges, or state mutations result from retry storms. `Idempotency-Key` support is verified if declared in the OpenAPI spec.

### 4.3 Schema Drift Tolerance
**Points: 25**

AI agents frequently send payloads with extra, missing, or reordered fields. Tests whether the API handles schema drift gracefully without crashing or producing 5xx errors.

**Test patterns:** Extra fields added, optional fields omitted, field order shuffled, string values sent where integers expected (and vice versa), null values in non-nullable fields.

**Pass Criteria:** Extra fields produce 200 (ignored) or 400 (rejected with clear message) — never 500. Missing optional fields are handled gracefully. All 400 responses include a machine-readable error code (not just a human-readable message string).

### 4.4 Quota Communication (Agent-Readable Rate Limiting)
**Points: 25**

AI agents need machine-readable quota state to make intelligent backoff decisions. This test verifies that rate limit responses include structured, agent-parseable information.

**Required response headers on 429:**
- `Retry-After: <seconds>` (mandatory)
- `X-RateLimit-Limit: <quota>` (mandatory)
- `X-RateLimit-Remaining: <remaining>` (mandatory)
- `X-RateLimit-Reset: <unix-timestamp>` (mandatory)

**Pass Criteria:** All four headers present on every 429 response. Agent must be able to parse retry timing without any human interpretation.

### 4.5 Structured Output Determinism
**Points: 30**

The PGL's EI receipt system relies on SHA-256 hashing of API responses for audit integrity. This requires that identical inputs produce byte-equivalent outputs (no random nonces, timestamps, or UUIDs in response bodies unless explicitly documented as non-deterministic fields).

**Pass Criteria:** For any declared deterministic endpoint, sending the same request 3× must produce byte-equivalent response bodies (excluding documented non-deterministic fields declared in the OpenAPI spec). Non-deterministic fields must be explicitly flagged in the spec with the `x-veklom-nondeterministic: true` extension.

---

## The Veklom Trust Certificate

APIs that pass all four pillars receive a **Veklom Trust Certificate**, minted via the PGL. The certificate is a signed JSON document containing:

```json
{
  "vabp_version": "1.0",
  "api_identifier": "<EI-assigned API ID>",
  "benchmark_timestamp": "<ISO 8601 UTC>",
  "pgl_root_hash": "<SHA-256 of all evidence log entries>",
  "total_score": 000,
  "pillar_scores": {
    "security": { "score": 000, "max": 350, "passed": true },
    "performance": { "score": 000, "max": 250, "passed": true },
    "compliance": { "score": 000, "max": 250, "passed": true },
    "agentic_ai": { "score": 000, "max": 150, "passed": true }
  },
  "badges_earned": [],
  "cold_start_p95_ms": 000,
  "warm_p95_ms": 000,
  "max_sustained_rps": 0000,
  "tls_version": "TLSv1.3",
  "certificate_signature": "<PGL private key signature>"
}
```

### Badge Reference

| Badge | Awarded When |
|---|---|
| `OWASP API Top 10 Pass` | Pillar 1 score ≥ 245 with zero BOLA/Shadow API failures |
| `NIST SP 800-204C Aligned` | Pillar 1 full pass + TLS validation pass |
| `FedRAMP-Aligned Architecture` | Pillar 3 full pass |
| `HIPAA-Addressable Controls` | PHI/PII exfiltration test score = 80/80 |
| `P95 Latency < Xms` | Displays measured warm p95 value from Pillar 2.1 |
| `Zero Data Leaks` | PHI/PII exfiltration test score = 80/80 |
| `Agentic-Ready ✓` | Pillar 4 full pass (≥ 105/150) |
| `PGL Integrated` | Pillar 3.3 full pass (100% EI receipt coverage) |

---

## Re-Certification Policy

- Certificates are valid for **12 months** from the benchmark timestamp
- Any **breaking API change** (new endpoint, auth schema change, OpenAPI spec update) triggers mandatory re-certification of affected pillars
- **Minor version updates** (bug fixes, non-breaking changes) require a re-run of Pillar 1.2 (Shadow API Discovery) only
- Re-certification runs are fully automated via the PGL benchmark harness

---

## Evidence Artifacts

All VABP benchmark runs produce the following evidence artifacts, stored in and linked from the PGL:

| Artifact | Description |
|---|---|
| `vabp_run_summary.json` | Machine-readable full score report |
| `pillar1_security_log.json` | All injection/auth test results with request/response pairs |
| `pillar2_performance_stats.json` | Raw latency percentiles, RPS curves, availability ratio |
| `pillar3_compliance_log.json` | TLS handshake details, PII scan results, PGL receipt audit |
| `pillar4_agentic_log.json` | Retry storm results, schema drift responses, determinism hashes |
| `pgl_evidence_chain.json` | Full SHA-256 chain of all test call EI receipts |

These artifacts are referenced in the Trust Certificate's `pgl_root_hash` field and are retrievable by any party with the certificate's API identifier.

---

## Changelog

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-14 | Veklom Engineering | Initial release. Four-pillar structure. Corrects prior NIST SP 800-228 reference (non-existent) to NIST SP 800-204C and SP 800-53 Rev 5. |
