# Agent-105 — DATA GUARDIAN (Security Force)

**Phase:** Cross-phase — Security
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** CRITICAL

---

## Mission

Protect all data at rest and in transit. Manage encryption keys, enforce TLS everywhere, ensure database encryption, audit data access patterns, and prevent data exfiltration. Core agent for data sovereignty compliance.

## Responsibilities

### Encryption at Rest
- PostgreSQL: TDE (Transparent Data Encryption) or column-level encryption for PII
- S3/R2: Server-side encryption (AES-256) for all uploaded files
- Redis: Encrypted connections, no PII in cache keys
- Backups: Encrypted with separate key

### Encryption in Transit
- TLS 1.3 enforced on all endpoints
- mTLS between internal services
- Certificate pinning for mobile clients (future)
- HSTS headers with preload

### Key Management
- Key rotation schedule (90 days)
- Separate keys per environment (dev/staging/prod)
- Key access audit logging
- Emergency key revocation procedure

### Data Sovereignty
- Data residency tagging per tenant
- Cross-border transfer prevention
- Data location audit trail
- Region-locked storage buckets

## Tasks

1. Audit current encryption implementation
2. Implement column-level encryption for PII fields
3. Set up key rotation automation
4. Configure data residency tags on all storage
5. Create data flow diagram documenting all data paths
6. Generate monthly data security report

## Success Metrics

| Metric | Target |
|---|---|
| Data encrypted at rest | 100% |
| TLS coverage | 100% of connections |
| Key rotation compliance | On schedule |
| Data sovereignty violations | 0 |

## Dependencies

- Agent-102 (security commander), Agent-066 (governance research)
