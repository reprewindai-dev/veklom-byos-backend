# Paying Veklom governed capabilities with x402

> Status: **TRANSITIONING TO CANONICAL CAPABILITY VERIFICATION**
>
> Do not use this document as proof that every historical paid route is current or externally verified. The old PayAPI catalog-era surface is being retired. External verification should target one canonical governed capability with payment, execution, output, evidence, and replay protection bound together.

## Verification rule

A successful x402 settlement is necessary for a paid capability, but it is not sufficient evidence that the capability worked.

The externally verifiable flow is:

1. discover the capability contract and live payment terms;
2. call the capability and receive an HTTP 402 challenge;
3. submit a valid payment proof;
4. retry the same logical request with a stable idempotency key;
5. execute only after governance authorization succeeds;
6. validate the returned output against the capability contract;
7. return a durable receipt/evidence reference binding payment, capability/version, request, output hash, and execution evidence;
8. reject payment-proof replay and idempotency conflicts.

## Current implementation note

The repository still contains historical route-level x402 middleware and pricing entries. Those entries are **not** the canonical external verification surface by themselves. See GitHub issues #173 and #174 for the replacement paid-execution verification suite and canonical capability selection.

Until #174 is complete, do not add new external PayAPI listings by expanding the historical route catalog or by using runtime in-memory route registration as a source of truth.

## Discovery

Clients should read live x402 configuration/discovery data from the deployed service rather than hard-coding treasury addresses, prices, or network metadata.

## Required evidence contract

A successful externally verified paid execution should expose, directly or through a receipt lookup:

- capability id and version;
- payment transaction/proof reference;
- request/idempotency identifier;
- governance decision/authority reference;
- execution identifier;
- output hash;
- evidence/receipt identifier;
- verification status/signature data sufficient to detect tampering and replay.

## Historical note

Older documentation listed many route-specific prices and described those routes as the public x402 product surface. That model is deprecated for external verification. Route pricing may remain internally while the platform converges on a capability-centric registry, but route presence or settlement alone must not be presented as proof of delivery.
