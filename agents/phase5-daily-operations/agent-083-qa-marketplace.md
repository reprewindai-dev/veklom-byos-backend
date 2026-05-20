# Agent-083 — QA (Marketplace)

**Phase:** Cross-phase — QA
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Test the full marketplace lifecycle: vendor registration, listing creation, file upload, review workflow, search/browse, purchase, and download.

## Test Cases

1. Vendor account creation and Stripe Connect onboarding
2. Listing creation with all fields
3. File upload via S3 presigned URLs
4. Listing submit → review → approve/reject workflow
5. Marketplace search and filtering
6. Listing detail page rendering
7. Purchase checkout flow
8. Post-purchase file download

## Dependencies

- Agent-001 (Stripe Connect), Agent-031 (vendor success), Agent-080 (QA lead)
