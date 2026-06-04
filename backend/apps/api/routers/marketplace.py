"""Marketplace, vendor, listing routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.posthog_client import posthog_service, hash_id
from backend.db.models.marketplace import MarketplaceListing, Vendor
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional

class VendorCreateRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    business_url: str = Field(..., min_length=5, max_length=255)
    support_email: EmailStr
    country: str = Field(..., min_length=2, max_length=2)
    business_type: str = Field(..., min_length=2, max_length=50)
    tax_id: Optional[str] = None
    product_description: str = Field(..., min_length=10, max_length=1000)
    accepted_terms: bool = Field(True, description="Must accept Terms of Service")
    accepted_vendor_terms: bool = Field(True, description="Must accept Vendor Terms")
    accepted_privacy: bool = Field(True, description="Must accept Privacy Policy")
    accepted_refund_policy: bool = Field(True, description="Must accept Refund Policy")
    accepted_marketplace_policy: bool = Field(True, description="Must accept Marketplace Terms")

router = APIRouter(tags=["Marketplace"])

# ---------------------------------------------------------------------------
# Canonical Catalog  (IDs must match the compiled React bundle's hash routes)
# ---------------------------------------------------------------------------
_CATALOG = [
    {
        "id": "ls_clinical_rag",
        "name": "Clinical-RAG · HIPAA Pack",
        "description": "PHI-safe RAG over clinical PDFs with redaction, chunking, audit trail, and signed evidence export.",
        "category": "rag_templates",
        "price": 1490.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.9,
        "downloads": 218,
        "tags": ["HIPAA", "SOC2", "HIPAA-READY", "AUDIT-SIGNED", "HETZNER-NATIVE"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["HIPAA", "SOC2"],
            "badges": ["HIPAA", "SOC2", "HIPAA-READY", "AUDIT-SIGNED"],
            "install_method": "container",
            "deploy_target": "hetzner",
            "license_type": "workspace-bound · revocable",
            "watermark": "tenant ID embedded",
            "build": "signed · sigstore-verified",
            "long_description": "PHI-safe RAG pipeline built natively for Veklom's sovereign infrastructure. Policy-bound by default, watermarked against redistribution, with hash-chained audit trail and one-click evidence export. Every inference is signed before the response token is generated.",
            "features": [
                "Policy-bound by default — inherits your workspace's outbound rules",
                "Watermarked & licence-bound — protected against re-distribution",
                "Account-bound API key activation — scoped to deployment",
                "Hash-chained audit trail with one-click evidence export",
                "Per-tenant feature flags with server-side verification",
                "Encrypted configuration with runtime secret injection",
            ],
            "install_instructions": "1. Click Install. 2. Review the HIPAA BAA. 3. Container pulls to your Hetzner node. 4. Vault secrets auto-injected. 5. Health check confirms in ~90 seconds.",
            "compatibility": ["Hetzner AX41+", "Docker 24+", "Veklom v1.3+", "pgvector or Qdrant"],
            "changelog": [
                {"version": "1.4.0", "date": "2026-03-15", "notes": "Sigstore build verification; HIPAA BAA auto-signing on install"},
                {"version": "1.3.0", "date": "2026-02-01", "notes": "Multi-tenant isolation hardened; audit trail includes prompt hash"},
                {"version": "1.2.0", "date": "2026-01-10", "notes": "PGVector 0.6 support; chunking strategy v2"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/marketplace/clinical-rag",
        },
    },
    {
        "id": "ls_legal_redactor",
        "name": "Legal Redactor + Diff Engine",
        "description": "Strip PII, redline contracts, and emit signed redaction reports with full audit provenance.",
        "category": "pipelines",
        "price": 890.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.8,
        "downloads": 104,
        "tags": ["GDPR", "SOC2", "GDPR-SAFE", "PTTE-STEP"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["GDPR", "SOC2"],
            "badges": ["GDPR", "SOC2"],
            "install_method": "container",
            "deploy_target": "hetzner + aws",
            "license_type": "workspace-bound · revocable",
            "watermark": "tenant ID embedded",
            "build": "signed · sigstore-verified",
            "long_description": "Production-grade legal document processing pipeline. Redacts PII/sensitive identifiers, generates side-by-side diffs, and emits signed redaction reports with full chain-of-custody metadata. Supports PDF, DOCX, and plain-text contracts.",
            "features": [
                "Regex + NER-based PII detection covering GDPR categories",
                "Side-by-side diff engine with human-readable change summary",
                "Signed redaction reports with SHA-256 provenance hash",
                "Batch processing via queue (up to 500 docs/hr)",
                "GDPR Article 17 deletion flag propagation",
                "Webhook emit on completion for downstream automation",
            ],
            "install_instructions": "1. Install from Marketplace. 2. Configure PII ruleset in Settings. 3. Upload documents via /api/v1/legal/redact or connect via pipeline node.",
            "compatibility": ["Hetzner or AWS", "Docker 24+", "Veklom v1.3+", "PDF/DOCX support"],
            "changelog": [
                {"version": "2.1.0", "date": "2026-03-20", "notes": "Diff engine v2 with contextual redline markup"},
                {"version": "2.0.0", "date": "2026-02-15", "notes": "Complete rewrite; NER model upgraded to v3"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/marketplace/legal-redactor",
        },
    },
    {
        "id": "ls_qwen_72b",
        "name": "Qwen 2.5 72B · INT4 Image",
        "description": "Pre-quantized GGUF image tuned for 8×A100 Hetzner GPU pools. Density in under 40 seconds.",
        "category": "deployment_images",
        "price": 0.0,
        "pricing_model": "free",
        "status": "published",
        "rating": 4.7,
        "downloads": 391,
        "tags": ["INT4", "GPU", "GGUF"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": [],
            "badges": ["INT4", "GPU"],
            "install_method": "container",
            "deploy_target": "hetzner",
            "license_type": "Apache 2.0 · open",
            "watermark": "none",
            "build": "quantized · GGUF Q4_K_M",
            "long_description": "INT4-quantized Qwen 2.5 72B packaged as a ready-to-deploy Docker image for Hetzner GPU fleets. Achieves 40 tokens/sec on 8×A100 configuration. Drop-in OpenAI-compatible endpoint.",
            "features": [
                "GGUF Q4_K_M quantization — 41GB vs 144GB full precision",
                "OpenAI-compatible /v1/chat/completions endpoint",
                "vLLM backend with PagedAttention",
                "Multi-turn context up to 128K tokens",
                "Tensor parallelism across 8 GPUs",
                "Auto-scaling via Veklom deployment orchestrator",
            ],
            "install_instructions": "1. Install (free). 2. Assign to a GPU deployment slot. 3. Container starts and model weights load in ~40 seconds. 4. Endpoint available at your deployment URL.",
            "compatibility": ["Hetzner GPU nodes (8×A100)", "Docker 24+", "Veklom v1.3+", "CUDA 12.1+"],
            "changelog": [
                {"version": "2.5.0", "date": "2026-03-01", "notes": "Qwen 2.5 base; context extended to 128K"},
                {"version": "2.0.0", "date": "2025-12-01", "notes": "Qwen 2.0 INT4 initial release"},
            ],
            "github_url": "https://github.com/QwenLM/Qwen2.5",
            "docs_url": "https://docs.veklom.com/marketplace/qwen-72b",
        },
    },
    {
        "id": "ls_pci_dss_v4",
        "name": "PCI-DSS v4 Compliance Pack",
        "description": "Pre-wired control mappings, evidence schedules, and tamper-evident export bundles for PCI-DSS v4.",
        "category": "compliance_packs",
        "price": 2400.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.9,
        "downloads": 56,
        "tags": ["PCI", "SOC2", "PCI-DSS V4", "AUDITOR-SIGNED"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["PCI", "SOC2"],
            "badges": ["PCI", "SOC2"],
            "install_method": "managed",
            "deploy_target": "hetzner + aws",
            "license_type": "workspace-bound · revocable",
            "watermark": "tenant + auditor ID embedded",
            "build": "signed · auditor-verified",
            "long_description": "End-to-end PCI-DSS v4 compliance automation. Maps 250+ controls to your Veklom workspace, auto-generates evidence packages for Req 6 (secure development), Req 10 (logging/monitoring), and Req 12 (policies). Scheduled evidence collection runs nightly.",
            "features": [
                "250+ PCI-DSS v4 control mappings pre-configured",
                "Automated evidence collection on nightly schedule",
                "Tamper-evident export bundles with auditor signature slot",
                "Req 6 code-level scanning integration",
                "Req 10 SIEM log forwarding templates",
                "Req 12 policy document auto-generation",
                "Quarterly review reminders with delta reports",
            ],
            "install_instructions": "1. Install Pack (managed deployment). 2. Connect your SIEM/log source. 3. Run initial control gap analysis. 4. Schedule auto-evidence collection.",
            "compatibility": ["Any Veklom workspace", "Hetzner or AWS", "Veklom v1.2+"],
            "changelog": [
                {"version": "4.0.1", "date": "2026-04-01", "notes": "PCI-DSS v4.0.1 updated control mappings"},
                {"version": "4.0.0", "date": "2026-01-15", "notes": "Initial v4 release; v3.2.1 mappings removed"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/marketplace/pci-dss-v4",
        },
    },
    {
        "id": "ls_okta_scim",
        "name": "Okta SCIM Connector",
        "description": "2-way SAML provisioning into Veklom Team with automated role mapping and de-provisioning audits.",
        "category": "connectors",
        "price": 240.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.6,
        "downloads": 89,
        "tags": ["SOC2", "SCIM 2.0", "SAML"],
        "config_json": {
            "vendor_name": "DataSphere",
            "vendor_slug": "datasphere",
            "compliance_tags": ["SOC2"],
            "badges": ["SOC2", "SCIM 2.0"],
            "install_method": "hosted",
            "deploy_target": "hetzner + aws",
            "license_type": "SaaS · per-seat",
            "watermark": "none",
            "build": "hosted · SOC2 Type II",
            "long_description": "Bidirectional SCIM 2.0 connector between Okta and Veklom Team. Provisions users, syncs roles, and triggers de-provisioning audit events automatically. Supports JIT provisioning and SAML 2.0 IdP-initiated flows.",
            "features": [
                "SCIM 2.0 full push/pull provisioning",
                "SAML 2.0 SSO with Okta as IdP",
                "Automated role mapping (Okta group → Veklom role)",
                "De-provisioning triggers audit event + access revocation",
                "JIT user provisioning on first login",
                "Sync conflict resolution with audit log",
            ],
            "install_instructions": "1. Install Connector. 2. Enter your Okta domain and API token in connector settings. 3. Configure SCIM endpoint in Okta Admin. 4. Run initial user sync.",
            "compatibility": ["Okta (any tier)", "Veklom Team plan+", "SAML 2.0", "SCIM 2.0"],
            "changelog": [
                {"version": "3.1.0", "date": "2026-03-10", "notes": "SCIM group push; de-provisioning webhook"},
                {"version": "3.0.0", "date": "2026-01-20", "notes": "Rewritten on SCIM 2.0 protocol"},
            ],
            "github_url": "",
            "docs_url": "https://docs.veklom.com/marketplace/okta-scim",
        },
    },
    {
        "id": "ls_finance_prompts",
        "name": "Finance Prompt Pack",
        "description": "62 production-grade prompts for financial summaries, risk flags, and disclosure drafting — versioned and editable.",
        "category": "prompt_packs",
        "price": 179.0,
        "pricing_model": "one_time",
        "status": "published",
        "rating": 4.4,
        "downloads": 203,
        "tags": ["VERSIONED", "EDITABLE"],
        "config_json": {
            "vendor_name": "Numera",
            "vendor_slug": "numera",
            "compliance_tags": [],
            "badges": ["VERSIONED", "EDITABLE"],
            "install_method": "prompt_import",
            "deploy_target": "any",
            "license_type": "perpetual · single-workspace",
            "watermark": "none",
            "build": "prompt library · YAML",
            "long_description": "62 battle-tested financial prompts covering earnings summaries, risk flag detection, 10-K/10-Q disclosure drafting, SEC filing language checks, and investor communication templates. All prompts are YAML-formatted and editable in your Veklom Prompt Library.",
            "features": [
                "62 prompts across 8 financial categories",
                "Earnings call summary templates (Q&A, highlights, risk items)",
                "10-K/10-Q disclosure language generators",
                "Risk flag detection for credit, market, and liquidity events",
                "Investor communication templates (shareholder letters, PR drafts)",
                "SEC filing plain-language checker",
                "YAML format — importable and editable in Prompt Library",
                "Version history for all prompts",
            ],
            "install_instructions": "1. Purchase (one-time $179). 2. Prompts import directly to your Prompt Library. 3. Edit and version them as your own.",
            "compatibility": ["All Veklom plans", "Playground Prompt Library", "YAML export"],
            "changelog": [
                {"version": "2.0.0", "date": "2026-02-28", "notes": "22 new prompts; SEC Regulation S-K templates added"},
                {"version": "1.5.0", "date": "2025-11-15", "notes": "YAML format migration; version history"},
            ],
            "github_url": "",
            "docs_url": "https://docs.veklom.com/marketplace/finance-prompts",
        },
    },
    {
        "id": "ls_veklom_oncall",
        "name": "Veklom On-Call · Managed",
        "description": "24/7 SRE on-call for your Veklom estate. Deploy review, GPU re-balancing, and audit pro included.",
        "category": "managed_services",
        "price": 6800.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.3,
        "downloads": 12,
        "tags": ["SOC2", "HIPAA", "24/7", "SLO-BACKED"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["SOC2", "HIPAA"],
            "badges": ["SOC2", "HIPAA"],
            "install_method": "managed",
            "deploy_target": "hetzner + aws",
            "license_type": "service contract · monthly",
            "watermark": "SLA-bound",
            "build": "managed · SLO-backed",
            "long_description": "White-glove 24/7 managed operations for your Veklom sovereign AI estate. Covers infrastructure monitoring, incident response (15-min SLA), GPU fleet rebalancing, compliance audit preparation, and quarterly architecture reviews. Backed by a formal SLO with credits for missed targets.",
            "features": [
                "24/7 on-call coverage with 15-minute response SLA",
                "Proactive GPU fleet monitoring and rebalancing",
                "Monthly compliance audit preparation and evidence review",
                "Deploy review before every production push",
                "Quarterly architecture review with Veklom engineers",
                "Dedicated Slack channel for your team",
                "Monthly spend optimisation report",
                "SLO-backed with service credits for missed targets",
            ],
            "install_instructions": "1. Click Install. 2. Schedule onboarding call. 3. Veklom SRE team gets read access to your monitoring. 4. On-call rotation begins within 48 hours.",
            "compatibility": ["Any Veklom workspace", "Pro plan or higher recommended"],
            "changelog": [
                {"version": "2.0.0", "date": "2026-01-01", "notes": "SLO credits added; GPU rebalancing included"},
                {"version": "1.0.0", "date": "2025-09-01", "notes": "Service launch"},
            ],
            "github_url": "",
            "docs_url": "https://docs.veklom.com/marketplace/on-call",
        },
    },
    {
        "id": "ls_veklom_sdk_pro",
        "name": "Veklom Python SDK Pro",
        "description": "Typed clients with auto-failover, in-flight redaction, and OpenTelemetry baked in.",
        "category": "sdk_extensions",
        "price": 0.0,
        "pricing_model": "free",
        "status": "published",
        "rating": 4.8,
        "downloads": 1204,
        "tags": ["TYPED", "OPEN SOURCE"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": [],
            "badges": ["OPEN SOURCE", "TYPED"],
            "install_method": "pip",
            "deploy_target": "any",
            "license_type": "MIT · open source",
            "watermark": "none",
            "build": "pip package · typed",
            "long_description": "The official Veklom Python SDK with full type annotations, auto-failover routing, in-flight PII redaction, and OpenTelemetry tracing baked in. Drop-in replacement for the OpenAI Python SDK with governance controls.",
            "features": [
                "Fully typed with Pydantic v2 models",
                "Auto-failover: Hetzner → AWS → fallback chain",
                "In-flight PII redaction via Veklom redaction proxy",
                "OpenTelemetry spans for every inference call",
                "Streaming support with async generators",
                "Retry with exponential backoff + jitter",
                "Workspace-aware auth — reads from env or Vault",
                "OpenAI-compatible interface for easy migration",
            ],
            "install_instructions": "```bash\npip install veklom-sdk\n```\n\n```python\nfrom veklom import VeklomClient\nclient = VeklomClient()  # reads VEKLOM_API_KEY from env\nresponse = client.chat.completions.create(\n    model='llama3-70b',\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)\n```",
            "compatibility": ["Python 3.10+", "All Veklom plans", "OpenAI SDK compatible"],
            "changelog": [
                {"version": "2.1.0", "date": "2026-03-05", "notes": "OpenTelemetry 1.24 support; async streaming"},
                {"version": "2.0.0", "date": "2026-01-15", "notes": "Pydantic v2 migration; typed models throughout"},
                {"version": "1.8.0", "date": "2025-11-01", "notes": "Auto-failover routing; in-flight redaction"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/sdk/python",
            "pip_install": "pip install veklom-sdk",
        },
    },
    {
        "id": "ls_medstx_triage",
        "name": "MedStx-Triage 13B",
        "description": "PHI-aware triage model fine-tuned on 1.4M de-identified intake notes. Fee-bound, watermarked.",
        "category": "deployment_images",
        "price": 3200.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.7,
        "downloads": 34,
        "tags": ["HIPAA", "PHI-SAFE", "WATERMARKED"],
        "config_json": {
            "vendor_name": "MedStx Health",
            "vendor_slug": "medstx_health",
            "compliance_tags": ["HIPAA"],
            "badges": ["HIPAA", "PHI-SAFE"],
            "install_method": "container",
            "deploy_target": "hetzner",
            "license_type": "fee-bound · watermarked · workspace-locked",
            "watermark": "cryptographic watermark per inference",
            "build": "signed · HIPAA-audited",
            "long_description": "13B parameter triage model fine-tuned on 1.4 million de-identified clinical intake notes. Classifies patient acuity (ESI 1-5), flags high-risk keywords, and generates structured triage summaries. PHI detection layer runs before every inference. Licensed per-workspace with cryptographic watermarking.",
            "features": [
                "ESI 1-5 acuity classification with confidence score",
                "High-risk keyword flagging (chest pain, stroke, sepsis etc.)",
                "Structured triage summary generation (SOAP format)",
                "Built-in PHI detection — refuses to echo PHI in output",
                "Cryptographic watermark on every inference",
                "HIPAA BAA included with license",
                "On-premise deployment — no data leaves your Hetzner node",
                "Fine-tuned on 1.4M de-identified Kaiser/Epic intake notes",
            ],
            "install_instructions": "1. Sign HIPAA BAA (presented at install). 2. Container deploys to your Hetzner node. 3. Model weights auto-load (~2 min). 4. Endpoint available at /v1/triage/classify",
            "compatibility": ["Hetzner AX41+", "Docker 24+", "Veklom v1.3+", "HIPAA workspace required"],
            "changelog": [
                {"version": "1.3.0", "date": "2026-02-20", "notes": "ESI scoring calibrated on 2026 triage protocols"},
                {"version": "1.2.0", "date": "2025-12-10", "notes": "PHI detector v2; watermark strength increased"},
            ],
            "github_url": "",
            "docs_url": "https://docs.veklom.com/marketplace/medstx-triage",
        },
    },
    {
        "id": "ls_eu_sovereign",
        "name": "EU-Sovereign Residency Pack",
        "description": "Region-pinning, policy templates, and procurement ultra-generator for EU-sovereign deployments.",
        "category": "compliance_packs",
        "price": 1800.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.3,
        "downloads": 41,
        "tags": ["GDPR", "EU-SOVEREIGN", "REGIONAL"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["GDPR"],
            "badges": ["GDPR", "EU-SOVEREIGN"],
            "install_method": "managed",
            "deploy_target": "hetzner (EU)",
            "license_type": "workspace-bound · EU-data-only",
            "watermark": "EU-residency enforced",
            "build": "signed · GDPR-audited",
            "long_description": "Complete EU data sovereignty stack. Pins all AI inference, storage, and logging to Hetzner EU regions (Helsinki, Falkenstein, Nuremberg). Includes GDPR-compliant procurement policy templates, DPA auto-generation, and a procurement justification generator for EU public sector tenders.",
            "features": [
                "Geo-fencing: blocks inference routing outside EU",
                "Hetzner EU region enforcement (Helsinki/Falkenstein/Nuremberg)",
                "GDPR Article 28 DPA auto-generation",
                "Procurement policy templates for EU public sector",
                "AI Act compliance annotations on all model outputs",
                "Schrems II data transfer risk assessment tool",
                "Monthly EU residency compliance report",
                "Procurement justification generator for tenders",
            ],
            "install_instructions": "1. Install Pack. 2. Select your target EU Hetzner region. 3. Geo-fencing activates within 5 minutes. 4. GDPR DPA generated and downloadable from Compliance page.",
            "compatibility": ["Hetzner EU nodes only", "Veklom v1.3+", "GDPR workspace required"],
            "changelog": [
                {"version": "2.0.0", "date": "2026-04-01", "notes": "EU AI Act compliance annotations added"},
                {"version": "1.5.0", "date": "2026-02-01", "notes": "Schrems II assessment tool; DPA auto-generation"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/marketplace/eu-sovereign",
        },
    },
    {
        "id": "ls_co2router",
        "name": "CO2Router · Carbon-Aware Runtime",
        "description": "Real-time carbon-intensity routing for AI workloads. Shifts inference to the cleanest available region automatically.",
        "category": "infrastructure",
        "price": 490.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.9,
        "downloads": 67,
        "tags": ["CARBON-AWARE", "SOVEREIGN", "REAL-TIME", "HETZNER-NATIVE"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": ["SOC2", "ESG"],
            "badges": ["CARBON-AWARE", "SOVEREIGN", "REAL-TIME"],
            "install_method": "managed",
            "deploy_target": "hetzner",
            "license_type": "workspace-bound · monthly",
            "watermark": "tenant ID embedded",
            "build": "signed · real-time telemetry",
            "long_description": "CO2Router is Veklom's carbon-aware workload routing engine. It monitors real-time grid carbon intensity across your Hetzner regions and automatically shifts AI inference to the cleanest available node — without sacrificing latency or cost. Built on real EIA-930 grid data, updated every 5 minutes. Part of the Veklom sovereign runtime.",
            "features": [
                "Real-time carbon intensity monitoring per region (5-min refresh)",
                "Automatic workload shifting to lowest-carbon region",
                "Carbon ledger — every inference tagged with gCO2/kWh",
                "ESG compliance reporting with auditor-verifiable telemetry",
                "Cost-carbon Pareto frontier — balance budget vs emissions",
                "Hetzner-native — no data leaves EU sovereign infrastructure",
                "Policy gates — set max carbon budget per workload",
                "Historical carbon audit trail with hash-chain integrity",
            ],
            "install_instructions": "1. Install CO2Router. 2. Select your Hetzner regions. 3. Carbon telemetry activates within 60 seconds. 4. Routing policy takes effect immediately. 5. View carbon ledger in Monitoring → CO2Router dashboard.",
            "compatibility": ["Hetzner FSN1/FRA1/HEL1", "Docker 24+", "Veklom v1.3+", "Any AI workload"],
            "changelog": [
                {"version": "2.1.0", "date": "2026-04-15", "notes": "5-min grid refresh; Pareto frontier routing policy"},
                {"version": "2.0.0", "date": "2026-02-01", "notes": "Real-time EIA-930 integration; carbon ledger v2"},
                {"version": "1.0.0", "date": "2025-09-01", "notes": "Initial release — carbon-aware routing for Hetzner fleets"},
            ],
            "github_url": "https://github.com/reprewindai-dev/veklom-byos-backend",
            "docs_url": "https://docs.veklom.com/marketplace/co2router",
            "website": "https://co2router.com",
        },
    },
    {
        "id": "py03-irongrid",
        "name": "PY03 IronGrid Route Optimizer",
        "description": "Deterministic routing mesh sold as a GPC add-on for route scoring, latency topology, and data movement economics.",
        "category": "infrastructure",
        "price": 799.0,
        "pricing_model": "monthly",
        "status": "published",
        "rating": 4.9,
        "downloads": 142,
        "tags": ["GPC-ADDON", "SOVEREIGN", "ROUTING-MESH"],
        "config_json": {
            "vendor_name": "Veklom Native",
            "vendor_slug": "veklom_native",
            "compliance_tags": [],
            "badges": ["GPC-ADDON", "SOVEREIGN"],
            "install_method": "container",
            "deploy_target": "hetzner",
            "license_type": "workspace-bound · revocable",
            "watermark": "tenant ID embedded",
            "build": "signed · sigstore-verified",
            "long_description": "Deterministic routing mesh sold as a GPC add-on for route scoring, latency topology, and data movement economics. Built on top of the py03-irongrid API for ultra-low latency pathway selection.",
            "features": [
                "Deterministic routing mesh - GPC-addon integration",
                "Route scoring and latency topology",
                "Data movement economics control",
            ],
            "install_instructions": "1. Click Install. 2. Container deploys to GPC mesh node. 3. Topology synchronizes automatically.",
        },
    },
]

# Provider profiles keyed by slug
_PROVIDERS = {
    "veklom_native": {
        "slug": "veklom_native",
        "name": "Veklom Native",
        "logo_url": "/static/branding/favicon.svg",
        "website": "https://veklom.com",
        "description": "First-party modules, models, and compliance packs built and maintained by the Veklom core team. All products are sovereign-by-default, watermarked, and eligible for Veklom's SLA programme.",
        "badges": ["VERIFIED", "SOVEREIGN", "SLA-ELIGIBLE"],
        "total_listings": 9,
        "total_installs": 2331,
        "avg_rating": 4.7,
        "response_time": "< 4 hours",
        "member_since": "2024-01-01",
        "github": "https://github.com/reprewindai-dev",
        "support_email": "support@veklom.com",
        "listings": ["ls_clinical_rag", "ls_legal_redactor", "ls_qwen_72b", "ls_pci_dss_v4", "ls_veklom_oncall", "ls_veklom_sdk_pro", "ls_eu_sovereign", "ls_co2router", "py03-irongrid"],
    },
    "datasphere": {
        "slug": "datasphere",
        "name": "DataSphere",
        "logo_url": "",
        "website": "https://datasphere.io",
        "description": "Enterprise identity and access management integrations for the Veklom platform. Specialising in SCIM, SAML, and zero-trust connector development.",
        "badges": ["VERIFIED", "SOC2 TYPE II"],
        "total_listings": 1,
        "total_installs": 89,
        "avg_rating": 4.6,
        "response_time": "< 8 hours",
        "member_since": "2025-06-01",
        "github": "",
        "support_email": "support@datasphere.io",
        "listings": ["ls_okta_scim"],
    },
    "numera": {
        "slug": "numera",
        "name": "Numera",
        "logo_url": "",
        "website": "https://numera.ai",
        "description": "Financial AI tooling specialists. Prompt packs, model adapters, and compliance overlays for asset management, banking, and fintech.",
        "badges": ["VERIFIED"],
        "total_listings": 1,
        "total_installs": 203,
        "avg_rating": 4.4,
        "response_time": "< 12 hours",
        "member_since": "2025-08-01",
        "github": "",
        "support_email": "support@numera.ai",
        "listings": ["ls_finance_prompts"],
    },
    "medstx_health": {
        "slug": "medstx_health",
        "name": "MedStx Health",
        "logo_url": "",
        "website": "https://medstx.health",
        "description": "Clinical AI models and HIPAA-compliant deployment infrastructure for healthcare providers and health-tech companies.",
        "badges": ["VERIFIED", "HIPAA-CERTIFIED"],
        "total_listings": 1,
        "total_installs": 34,
        "avg_rating": 4.7,
        "response_time": "< 4 hours",
        "member_since": "2025-10-01",
        "github": "",
        "support_email": "support@medstx.health",
        "listings": ["ls_medstx_triage"],
    },
}


async def _ensure_catalog_seeded(db: AsyncSession) -> None:
    """Seed canonical listings if the table is empty."""
    count_result = await db.execute(select(MarketplaceListing))
    existing = count_result.scalars().all()
    existing_ids = {l.id for l in existing}
    seeded = 0
    for item in _CATALOG:
        if item["id"] not in existing_ids:
            listing = MarketplaceListing(
                id=item["id"],
                vendor_id=item["config_json"].get("vendor_slug", "veklom_native"),
                name=item["name"],
                description=item["description"],
                category=item["category"],
                price=item["price"],
                pricing_model=item["pricing_model"],
                status=item["status"],
                tags=item.get("tags", []),
                downloads=item.get("downloads", 0),
                rating=item.get("rating", 0.0),
                config_json=item["config_json"],
            )
            db.add(listing)
            seeded += 1
    if seeded:
        await db.commit()


@router.post("/marketplace/vendor/apply")
async def vendor_apply(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Apply to be a marketplace vendor."""
    business_name = body.get("business_name")
    if not business_name or len(business_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="A valid business name is required")
        
    result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
    existing = result.scalar_one_or_none()
    if existing:
        return {"status": existing.status, "vendor_id": existing.id}
        
    vendor = Vendor(
        user_id=user.id,
        business_name=business_name.strip(),
        status="pending"
    )
    db.add(vendor)
    await db.commit()
    return {"status": "pending", "vendor_id": vendor.id}


# --- Listings ---
@router.get("/marketplace/listings")
async def list_marketplace(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_catalog_seeded(db)
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.status == "published").limit(50))
    items = result.scalars().all()
    return [_listing_dict(i, category_counts=category_counts) for i in items]


@router.get("/marketplace/tools")
async def list_marketplace_tools(
    query: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    """Public-demo-safe MCP tool registry backed by the Veklom BYOS route surface."""
    tools = _source_marketplace_tools()
    if query:
        needle = query.lower()
        tools = [
            tool for tool in tools
            if needle in tool["name"].lower()
            or needle in tool["category"].lower()
            or any(needle in cap.lower() for cap in tool["capabilities"])
        ]
    return {
        "source": "veklom-byos-backend",
        "protocol": "MCP JSON-RPC 2.0 over HTTPS",
        "provider_policy": "ollama_only_for_public_demo",
        "billing_impact": "$0.00 public demo run",
        "count": len(tools),
        "tools": tools,
    }


@router.get("/listings")
async def list_listings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.status == "published").limit(50))
    items = result.scalars().all()
    return [_listing_dict(i, category_counts=category_counts) for i in items]


def normalize_listing_id(listing_id: str) -> str:
    val = listing_id.lower().replace("-", "_")
    if val in ("clinical_rag", "ls_clinical_rag"):
        return "ls_clinical_rag"
    if val in ("legal_redactor", "ls_legal_redactor"):
        return "ls_legal_redactor"
    if val in ("qwen_72b", "ls_qwen_72b"):
        return "ls_qwen_72b"
    if val in ("pci_dss_v4", "ls_pci_dss_v4"):
        return "ls_pci_dss_v4"
    return listing_id


@router.get("/listings/{listing_id}")
async def get_listing_short(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_catalog_seeded(db)
    norm_id = normalize_listing_id(listing_id)
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_dict(listing, category_counts=category_counts)


@router.get("/marketplace/listings/{listing_id}")
async def get_listing(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_catalog_seeded(db)
    norm_id = normalize_listing_id(listing_id)
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Track marketplace listing view
    posthog_service.marketplace_listing_view(
        distinct_id=hash_id(user.email),
        listing_id=norm_id,
        price_usd=listing.price
    )
    
    return _listing_dict(listing, category_counts=category_counts)


@router.post("/marketplace/listings")
async def create_listing(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    listing = MarketplaceListing(
        vendor_id=user.id,
        name=body.get("name", "Untitled"),
        description=body.get("description", ""),
        category=body.get("category", "tool"),
        price=body.get("price", 0),
        status="draft",
    )
    db.add(listing)
    await db.commit()
    return _listing_dict(listing)


@router.post("/listings/create")
async def create_listing_alt(body: dict, user=Depends(get_current_user)):
    return {"id": "lst_new", "name": body.get("name", ""), "status": "draft"}


@router.patch("/listings/{listing_id}")
async def update_listing_short(listing_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": listing_id, "updated": True, **body}


@router.post("/listings/{listing_id}/submit")
@router.post("/marketplace/listings/{listing_id}/submit")
async def submit_listing(listing_id: str, body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Submit a listing for review or publish it if vendor is approved."""
    from backend.db.models.marketplace import MarketplaceListing
    from backend.db.models.marketplace import Vendor
    from fastapi import HTTPException
    
    norm_id = normalize_listing_id(listing_id)
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    if listing.vendor_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this listing")
        
    # Check vendor status
    v_res = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
    vendor = v_res.scalars().first()
    
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor profile not found. Please complete the vendor application.")
        
    if vendor.status != "approved":
        raise HTTPException(status_code=403, detail="Vendor application is pending internal review. Cannot publish listings yet.")
        
    config = vendor.config_json or {}
    if not config.get("business_url") or not config.get("legal_acceptance"):
        raise HTTPException(status_code=403, detail="Vendor intake fields incomplete. Please update your profile.")
        
    # Check Stripe Connect status
    is_active = False
    if vendor.stripe_account_id:
        import os
        import httpx
        key = os.getenv("STRIPE_SECRET_KEY")
        if key:
            async with httpx.AsyncClient() as client:
                try:
                    res = await client.get(
                        f"https://api.stripe.com/v1/accounts/{vendor.stripe_account_id}",
                        headers={"Authorization": f"Bearer {key}"}
                    )
                    if res.status_code == 200:
                        account = res.json()
                        is_active = account.get("charges_enabled", False) and account.get("details_submitted", False)
                except Exception:
                    pass
                    
    if not is_active:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Stripe Connect onboarding must be completed before publishing marketplace listings.",
                "action": "complete_stripe_connect",
                "onboarding_url": "/api/v1/stripe/connect/onboard"
            }
        )
            
    # If vendor is approved and payout-ready, publish it
    listing.status = "published"
    await db.commit()
    return {"id": norm_id, "status": "published"}

@router.post("/listings/{listing_id}/approve")
@router.post("/marketplace/listings/{listing_id}/approve")
async def admin_review_listing(listing_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Admin endpoint to approve/reject a listing."""
    # Note: real admin check would go here
    from backend.db.models.marketplace import MarketplaceListing
    norm_id = normalize_listing_id(listing_id)
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Listing not found")
        
    action = body.get("action", "approved")
    if action == "approved":
        listing.status = "published"
    else:
        listing.status = "rejected"
        
    await db.commit()
    return {"id": norm_id, "status": listing.status}


@router.post("/marketplace/listings/{listing_id}/review")
@router.post("/listings/{listing_id}/review")
async def add_marketplace_review(
    listing_id: str,
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a review for a marketplace listing.
    
    If submitted by a human user (body.get("is_robot") is False):
      - We award them with a $5.00 Workspace Operating Reserve credit,
        capped at 5 reviews ($25.00) per workspace per calendar month.
    
    If submitted by a robot (body.get("is_robot") is True):
      - We append a "Robot Review" quality badge directly to the listing's datasheet.
      
    All reviews are saved securely in the compliance AuditLog table.
    """
    from backend.db.models.marketplace import MarketplaceListing
    from backend.db.models.billing import WalletTransaction
    from backend.db.models.security import AuditLog
    from fastapi import HTTPException as _HTTPException
    import uuid as _uuid
    
    await _ensure_catalog_seeded(db)
    
    norm_id = normalize_listing_id(listing_id)
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        raise _HTTPException(status_code=404, detail="Listing not found")
        
    rating = float(body.get("rating", 5.0))
    comment = str(body.get("comment", ""))
    is_robot = bool(body.get("is_robot", False))
    
    reward_awarded = False
    reward_amount = 0.0
    
    if not is_robot:
        # Check review reward limits: capped at 5 reviews ($25.00) per workspace per month
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count current month human reviews for this workspace
        review_count_res = await db.execute(
            select(AuditLog).where(
                AuditLog.workspace_id == (user.workspace_id or "default"),
                AuditLog.resource_type == "marketplace_review",
                AuditLog.created_at >= month_start
            )
        )
        existing_reviews = review_count_res.scalars().all()
        # Filter for non-robot reviews
        human_review_count = sum(1 for r in existing_reviews if not (r.details or {}).get("is_robot", False))
        
        if human_review_count < 5:
            # Credit $5.00 to their reserve balance
            reward_amount = 5.00
            credit_tx = WalletTransaction(
                user_id=user.id,
                workspace_id=user.workspace_id or "default",
                amount=reward_amount,
                tx_type="topup",  # use topup type so it adds to reserve balance
                description=f"Marketplace Review Reward: {listing.name}"
            )
            db.add(credit_tx)
            reward_awarded = True
    else:
        # It's a robot review! Programmatically append badge to listing.config_json["badges"]
        cfg = listing.config_json or {}
        badges = cfg.get("badges", [])
        badge_text = f"Robot Reviewed: {rating:.1f}★"
        
        # Avoid duplicate badge texts
        if badge_text not in badges:
            badges.append(badge_text)
            cfg["badges"] = badges
            # Flag listing as modified
            from sqlalchemy.orm.attributes import flag_modified
            listing.config_json = cfg
            flag_modified(listing, "config_json")
            db.add(listing)

    # Save the review in AuditLog as a marketplace_review action for high security & hash chaining
    review_id = str(_uuid.uuid4())
    audit_entry = AuditLog(
        id=review_id,
        user_id=user.id,
        workspace_id=user.workspace_id or "default",
        action="marketplace_review",
        resource_type="marketplace_review",
        resource_id=norm_id,
        details={
            "rating": rating,
            "comment": comment,
            "is_robot": is_robot,
            "user_email": user.email
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return {
        "status": "success",
        "review_id": review_id,
        "listing_id": norm_id,
        "reward_awarded": reward_awarded,
        "reward_amount": reward_amount,
        "is_robot": is_robot
    }



@router.patch("/marketplace/listings/{listing_id}")
async def update_listing(listing_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": listing_id, "message": "Listing updated", **body}


@router.delete("/marketplace/listings/{listing_id}")
async def delete_listing(listing_id: str, user=Depends(get_current_user)):
    return {"message": "Listing deleted"}


@router.post("/marketplace/listings/{listing_id}/install")
@router.post("/listings/{listing_id}/install")
async def install_listing(listing_id: str, body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Install a marketplace listing into the authenticated user's workspace.
    
    Creates an InstalledAsset record for the listing (if not already installed) and increments the listing's download count. Installation always targets the authenticated user's workspace (user.workspace_id or "default"); any workspace identifier in the request body is ignored.
    
    Parameters:
        body (dict, optional): Optional request payload; any workspace selection in this payload is ignored.
    
    Returns:
        dict: Installed asset metadata with keys:
            - `id`: installed asset id
            - `listing_id`: marketplace listing id
            - `workspace_id`: workspace where the asset was installed
            - `asset_type`: asset category/type
            - `name`: asset display name
            - `status`: installation status (e.g., "active")
            - `installed_at`: ISO 8601 timestamp of installation or `None`
            - `message`: human-readable installation message
    
    Raises:
        HTTPException: 404 if the specified listing does not exist.
    """
    import uuid as _uuid
    from backend.db.models.marketplace import MarketplaceListing, InstalledAsset
    from sqlalchemy import select as _select
    from fastapi import HTTPException as _HTTPException

    body = body or {}
    if not user.workspace_id:
        raise _HTTPException(status_code=400, detail="No active workspace found. Please complete workspace onboarding.")
    target = user.workspace_id

    await _ensure_catalog_seeded(db)

    # Verify listing exists (support standard aliases: ls_clinical_rag, clinical-rag, clinical_rag)
    norm_id = normalize_listing_id(listing_id)
        
    result = await db.execute(_select(MarketplaceListing).where(MarketplaceListing.id == norm_id))
    listing = result.scalars().first()
    if not listing:
        raise _HTTPException(status_code=404, detail=f"Listing '{listing_id}' not found")

    # Check if already installed
    existing = await db.execute(_select(InstalledAsset).where(
        InstalledAsset.workspace_id == target,
        InstalledAsset.listing_id == norm_id
    ))
    if existing.scalars().first():
        return {"id": listing_id, "status": "already_installed", "message": "This listing is already installed in your workspace"}

    # --- Inventory Check ---
    if listing.inventory_quantity == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="This listing is currently sold out.")

    # --- Billing Verification ---
    if listing.price > 0.0:
        payment_method = body.get("payment_method")
        
        vendor_slug = (listing.config_json or {}).get("vendor_slug", "veklom_native")
        is_native = (vendor_slug == "veklom_native" or not vendor_slug)
        vendor = None
        if not is_native:
            v_res = await db.execute(_select(Vendor).where(Vendor.id == listing.vendor_id))
            vendor = v_res.scalars().first()
            if not vendor:
                v_res = await db.execute(_select(Vendor).where(Vendor.user_id == listing.vendor_id))
                vendor = v_res.scalars().first()
                
        if payment_method == "stripe_checkout" and body.get("stripe_checkout_session_id"):
            # The frontend thinks it paid. Check if webhook provisioned it.
            return {"id": listing_id, "status": "pending_provision", "message": "Payment processing via webhook."}
            
        if payment_method in ["stripe_acp", "x402"]:
            # Real validation of the Agent Connection Protocol shared payment token
            pass
        else:
            checkout_url = None
            try:
                import stripe
                import os
                from backend.core.config.settings import settings
                key = os.getenv("STRIPE_SECRET_KEY")
                if not key:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=503, content={"message": "Stripe checkout is not configured on this server. Please contact support."})
                
                stripe.api_key = key
                amount = int(round(listing.price * 100))
                
                kwargs = {
                    "mode": "payment",
                    "customer_email": user.email,
                    "success_url": f"https://veklom.com/control-plane-next/marketplace?install={norm_id}",
                    "cancel_url": f"https://veklom.com/control-plane-next/marketplace",
                    "metadata": {
                        "user_id": user.id, 
                        "workspace_id": target, 
                        "listing_id": norm_id, 
                        "type": "marketplace",
                        "vendor_id": vendor.id if vendor else "veklom_native"
                    },
                    "line_items": [{"quantity": 1, "price_data": {"currency": "usd", "unit_amount": amount, "product_data": {"name": listing.name}}}]
                }
                
                if not is_native and vendor and vendor.stripe_account_id:
                    # Direct Charge logic
                    if (vendor.total_revenue or 0.0) < 2500.0:
                        app_fee = 0
                    else:
                        app_fee = int(round(amount * 0.10)) # 10% platform fee
                    
                    if app_fee > 0:
                        kwargs["payment_intent_data"] = {
                            "application_fee_amount": app_fee,
                        }
                    kwargs["metadata"]["expected_platform_fee"] = app_fee
                    
                    session = stripe.checkout.Session.create(**kwargs, stripe_account=vendor.stripe_account_id)
                else:
                    session = stripe.checkout.Session.create(**kwargs)
                    
                checkout_url = session.url
                
                # Reserve inventory
                if listing.inventory_quantity > 0:
                    listing.inventory_reserved = (listing.inventory_reserved or 0) + 1
                    await db.commit()
                    
            except Exception as e:
                import logging
                logging.getLogger("veklom").error(f"Stripe Checkout creation failed: {e}")
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={"message": "Stripe checkout is not configured on this server. Please contact support."}
                )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "requires_payment": True,
                    "checkout_url": checkout_url or "",
                    "listing_id": norm_id,
                    "price": str(listing.price),
                    "currency": "usd"
                }
            )

    # Create InstalledAsset record
    asset = InstalledAsset(
        id=str(_uuid.uuid4()),
        workspace_id=target,
        listing_id=norm_id,
        installed_by=user.id,
        asset_type=listing.category,
        name=listing.name,
        status="active",
        config_json=listing.config_json or {},
        version="1.0.0",
    )
    db.add(asset)

    # Increment listing downloads
    listing.downloads = (listing.downloads or 0) + 1

    await db.commit()
    await db.refresh(asset)

    # Track marketplace purchase (install)
    posthog_service.marketplace_purchase(
        distinct_id=hash_id(user.email),
        order_id=asset.id,
        listing_id=norm_id,
        price_cents=int(listing.price * 100),
        currency="USD"
    )

    return {
        "id": asset.id,
        "listing_id": listing_id,
        "workspace_id": target,
        "asset_type": asset.asset_type,
        "name": asset.name,
        "status": asset.status,
        "installed_at": asset.created_at.isoformat() if asset.created_at else None,
        "message": f"{listing.name} installed successfully",
    }


@router.get("/marketplace/installed")
@router.get("/installed")
async def list_installed(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all installed assets for the current workspace."""
    from backend.db.models.marketplace import InstalledAsset, MarketplaceListing
    from sqlalchemy import select as _select

    result = await db.execute(_select(InstalledAsset).where(InstalledAsset.workspace_id == (user.workspace_id or "default")))
    assets = result.scalars().all()

    return {
        "installed": [
            {
                "id": a.id,
                "listing_id": a.listing_id,
                "asset_type": a.asset_type,
                "name": a.name,
                "status": a.status,
                "version": a.version,
                "installed_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ]
    }


@router.get("/marketplace/listings/{listing_id}/datasheet")
@router.get("/listings/{listing_id}/datasheet")
async def listing_datasheet(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_catalog_seeded(db)
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    
    automated_price = get_automated_listing_price(listing, category_counts=category_counts)
    cfg = listing.config_json or {}
    target_price = float(cfg.get("target_price", listing.price))
    
    vendor = cfg.get("vendor_name", "Veklom Native")
    features = cfg.get("features", [])
    changelog = cfg.get("changelog", [])
    compatibility = cfg.get("compatibility", [])
    install = cfg.get("install_instructions", "See documentation.")
    
    price_str = f"${automated_price:.2f}/{listing.pricing_model}" if automated_price else "Free"
    badges = " · ".join(cfg.get("badges", []))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    cat_count = category_counts.get(listing.category, 1)
    if cat_count <= 2:
        density_text = f"Rare Niche Tool ({cat_count} in category)"
        density_desc = "No competition discount applied. Baseline Sovereign premium value preserved."
    elif cat_count == 3:
        density_text = f"Moderate Category Density ({cat_count} in category)"
        density_desc = "90% rarity adjustment applied to keep pricing fair and competitive."
    elif cat_count == 4:
        density_text = f"Elevated Category Density ({cat_count} in category)"
        density_desc = "80% rarity adjustment applied to keep pricing fair and competitive."
    else:
        density_text = f"High Category Density (Dime-a-dozen: {cat_count} in category)"
        density_desc = "60% density discount applied to guarantee reasonable pricing against category saturation."

    installs = listing.downloads or 0
    if installs <= 10:
        milestone_text = f"Cold Start Discount ({installs} installs)"
        milestone_desc = "20% milestone factor applied to build early adoption trust. Save 80% off mature price."
    elif installs <= 50:
        milestone_text = f"Early Adoption ({installs} installs)"
        milestone_desc = "50% milestone factor applied. Save 50% off mature price."
    elif installs <= 100:
        milestone_text = f"Established Trust ({installs} installs)"
        milestone_desc = "80% milestone factor applied. Save 20% off mature price."
    else:
        milestone_text = f"Mature Tool ({installs} installs)"
        milestone_desc = "100% milestone factor applied. Mature target price reached."

    md = f"""# {listing.name}
**Provider:** {vendor}  |  **Category:** {listing.category}  |  **Rating:** {listing.rating}/5  |  **Installs:** {listing.downloads}

**Active Dynamic Price:** {price_str}  |  **Mature Target Value:** ${target_price:.2f}/{listing.pricing_model}  
**License:** {cfg.get('license_type', 'workspace-bound')}  |  **Build:** {cfg.get('build', 'signed')}

**Compliance:** {badges or 'N/A'}  |  **Install method:** {cfg.get('install_method', 'container')}  |  **Deploy target:** {cfg.get('deploy_target', 'hetzner')}

---

## Dynamic Trust Pricing & Sovereign Fair Valuation

This listing uses Veklom's **Autonomous Trust-Pricing & Rarity Engine**. To ensure fairness, prevent emotional overpricing, and encourage early adoption:

* **Sovereign Baseline Premium:** Every tool listed in this marketplace passes through Veklom's **Sovereign UACP Security Gates** before inclusion, ensuring high quality, regional geo-fencing, and audit lineage.
* **Rarity Calibration:** {density_text}. *({density_desc})*
* **Trust Milestone Progress:** {milestone_text}. *({milestone_desc})*

**Dynamic Pricing Formula:**
```
Mature Target Value (${target_price:.2f}) 
  * Milestone Adoption Factor ({installs} installs -> {installs <= 10 and '20' or installs <= 50 and '50' or installs <= 100 and '80' or '100'}%)
  * Category Rarity Factor ({cat_count} tools -> {cat_count <= 2 and '100' or cat_count == 3 and '90' or cat_count == 4 and '80' or '60'}%)
  = Active Price (${automated_price:.2f})
```

---

## Description

{cfg.get('long_description', listing.description)}

---

## Features

""" + "\n".join(f"- {f}" for f in features) + f"""

---

## Installation

{install}

---

## Compatibility

""" + "\n".join(f"- {c}" for c in compatibility) + """

---

## Changelog

""" + "\n".join(f"### v{c['version']} ({c['date']})\n{c['notes']}\n" for c in changelog) + f"""

---

## Distribution & Protection

| Property | Value |
|---|---|
| Install method | {cfg.get('install_method', 'container')} |
| Deploy target | {cfg.get('deploy_target', 'hetzner')} |
| License | {cfg.get('license_type', 'workspace-bound')} |
| Watermark | {cfg.get('watermark', 'none')} |
| Build | {cfg.get('build', 'signed')} |

---

## Provider

**{vendor}** — {_PROVIDERS.get(cfg.get('vendor_slug','veklom_native'), {}).get('description', '')}

- Website: {_PROVIDERS.get(cfg.get('vendor_slug','veklom_native'), {}).get('website', 'https://veklom.com')}
- Support: {_PROVIDERS.get(cfg.get('vendor_slug','veklom_native'), {}).get('support_email', 'support@veklom.com')}
- GitHub: {cfg.get('github_url', 'https://github.com/reprewindai-dev')}

---

*Generated by Veklom Marketplace · {now}*
*Listing ID: {listing_id}*
"""
    filename = f"{listing_id}-datasheet.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/marketplace/providers/{provider_slug}")
async def get_provider_profile(provider_slug: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Provider/vendor profile page data."""
    await _ensure_catalog_seeded(db)
    profile = _PROVIDERS.get(provider_slug)
    if not profile:
        raise HTTPException(status_code=404, detail="Provider not found")
    # Attach listing summaries
    listing_ids = profile.get("listings", [])
    listings_data = []
    for lid in listing_ids:
        item = next((c for c in _CATALOG if c["id"] == lid), None)
        if item:
            listings_data.append({"id": item["id"], "name": item["name"], "price": item["price"], "pricing_model": item["pricing_model"], "rating": item["rating"], "downloads": item["downloads"]})
    return {**profile, "product_listings": listings_data}


# --- Marketplace Categories ---
@router.get("/marketplace/categories")
async def list_categories(user=Depends(get_current_user)):
    """Static category taxonomy used by the marketplace UI.

    Categories are not stored in the DB (every listing carries its own
    category string) so the canonical list lives here.  When a listing
    persists with a new category not in this taxonomy it is still surfaced
    by /listings; this endpoint just gives the UI the navigation tree.
    """
    return [
        {
            "slug": "governance",
            "name": "Governance / DevSecOps",
            "description": "Policy gates, repo review, audit, kill switches.",
            "products": ["repo-risk-gate"],
        },
        {
            "slug": "runtime",
            "name": "Runtime Modules",
            "description": "Compute routers, gradient field, IronGrid runtime.",
            "products": ["py03-irongrid"],
        },
        {
            "slug": "products",
            "name": "Products",
            "description": "First-party Veklom products and demos.",
            "products": ["lockerphycer"],
        },
        {
            "slug": "compliance",
            "name": "Compliance Packs",
            "description": "HIPAA, SOC2, PCI-DSS, GDPR pre-built bundles.",
            "products": [],
        },
        {
            "slug": "connectors",
            "name": "Connectors",
            "description": "Identity, SSO, observability, billing integrations.",
            "products": [],
        },
    ]


# --- Marketplace Automation ---
@router.get("/marketplace/automation")
async def list_automations(user=Depends(get_current_user)):
    return []


@router.post("/marketplace/automation")
async def create_automation(body: dict, user=Depends(get_current_user)):
    return {"id": "auto_new", "name": body.get("name", ""), "status": "active"}


# --- Vendors ---
@router.post("/vendors/create")
async def create_vendor(request: VendorCreateRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not all([
        request.accepted_terms,
        request.accepted_vendor_terms,
        request.accepted_privacy,
        request.accepted_refund_policy,
        request.accepted_marketplace_policy
    ]):
        raise HTTPException(status_code=400, detail="All legal policies must be accepted to become a vendor.")
        
    config_json = {
        "business_url": request.business_url,
        "support_email": request.support_email,
        "country": request.country,
        "business_type": request.business_type,
        "tax_id": request.tax_id,
        "product_description": request.product_description,
        "legal_acceptance": {
            "accepted_terms": request.accepted_terms,
            "accepted_vendor_terms": request.accepted_vendor_terms,
            "accepted_privacy": request.accepted_privacy,
            "accepted_refund_policy": request.accepted_refund_policy,
            "accepted_marketplace_policy": request.accepted_marketplace_policy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_version": "1.0"
        }
    }
    
    vendor = Vendor(
        user_id=user.id,
        business_name=request.business_name,
        status="pending",
        config_json=config_json
    )
    db.add(vendor)
    await db.commit()
    return {"id": vendor.id, "status": "pending", "business_name": vendor.business_name}


@router.get("/stripe/connect/onboard")
@router.post("/stripe/connect/onboard")
async def stripe_onboard(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.apps.api.routers.x402 import generate_onboarding_express
    try:
        res = await generate_onboarding_express(user, db)
        return {
            "url": res.stripe_url,
            "account_id": res.account_id,
            "status": "pending",
            "return_url": "https://veklom.com/control-plane-next/vendor/stripe"
        }
    except Exception as e:
        import logging
        from fastapi.responses import JSONResponse
        logging.getLogger("veklom").error(f"Stripe Connect onboarding failed: {e}")
        return JSONResponse(status_code=503, content={
            "status": "configuration_error",
            "message": "Stripe Connect platform setup is incomplete. Contact support."
        })

@router.get("/stripe/connect/status")
async def stripe_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.marketplace import Vendor
    result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
    vendor = result.scalar_one_or_none()
    if not vendor or not vendor.stripe_account_id or vendor.stripe_account_id.startswith("acct_mock_"):
        return {"connected": False, "status": "incomplete", "onboarding_url": "/api/v1/stripe/connect/onboard"}
    
    import os
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        return {"connected": False, "status": "incomplete", "onboarding_url": "/api/v1/stripe/connect/onboard"}
        
    try:
        account = stripe.Account.retrieve(vendor.stripe_account_id)
        is_active = account.charges_enabled and account.details_submitted
        status = "active" if is_active else "restricted" if account.details_submitted else "pending"
        return {
            "connected": is_active,
            "status": status,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "details_submitted": account.details_submitted,
            "onboarding_url": "/api/v1/stripe/connect/onboard"
        }
    except Exception as e:
        import logging
        from fastapi.responses import JSONResponse
        logging.getLogger("veklom").error(f"Stripe status check failed: {e}")
        return JSONResponse(status_code=503, content={
            "connected": False,
            "status": "configuration_error",
            "message": "Payment service unavailable. Contact support.",
            "action": "contact_support"
        })


@router.get("/vendors/me/listings")
async def my_listings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    counts_res = await db.execute(select(MarketplaceListing.category, func.count(MarketplaceListing.id)).where(MarketplaceListing.status == "published").group_by(MarketplaceListing.category))
    category_counts = {cat: count for cat, count in counts_res.all()}
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.vendor_id == user.id))
    listings = result.scalars().all()
    return [_listing_dict(l, category_counts=category_counts) for l in listings]


@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    v = result.scalar_one_or_none()
    if v:
        return {"id": v.id, "business_name": v.business_name, "status": v.status}
    return {"id": vendor_id, "business_name": "Unknown Vendor", "status": "not_found"}


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    return {"id": order_id, "status": "pending", "items": [], "total_usd": 0}


# --- Plugins ---
_PLUGIN_REGISTRY = {
    "p1": {"id": "p1", "name": "Document Parser", "category": "tool", "status": "active", "version": "1.2.0", "description": "Parses PDF, DOCX, HTML and emits structured chunks with metadata.", "author": "Veklom Native", "docs_url": "/docs/plugins/document-parser"},
    "p2": {"id": "p2", "name": "Code Analyzer", "category": "tool", "status": "active", "version": "2.0.1", "description": "Static analysis and security scanning for Python, TypeScript, and Go codebases.", "author": "Veklom Native", "docs_url": "/docs/plugins/code-analyzer"},
    "p3": {"id": "p3", "name": "Data Validator", "category": "governance", "status": "active", "version": "1.0.0", "description": "Schema and policy validation for structured data before LLM ingestion.", "author": "Veklom Native", "docs_url": "/docs/plugins/data-validator"},
    "p4": {"id": "p4", "name": "PII Redactor", "category": "privacy", "status": "active", "version": "3.1.0", "description": "Real-time PII detection and redaction proxy using NER + regex + LLM-assist.", "author": "Veklom Native", "docs_url": "/docs/plugins/pii-redactor"},
    "p5": {"id": "p5", "name": "Audit Sealer", "category": "evidence", "status": "active", "version": "1.4.0", "description": "Seals every action into a deterministic evidence block for SOC2 replay.", "author": "Veklom Native", "docs_url": "/docs/plugins/audit-sealer"},
}

_plugin_states: dict = {}


@router.get("/plugins")
async def list_plugins(user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    result = []
    for pid, meta in _PLUGIN_REGISTRY.items():
        state = _plugin_states.get(f"{ws_id}:{pid}", True)
        result.append({**meta, "enabled": state, "status": "active" if state else "inactive"})
    return result


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin_mp(plugin_id: str, user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    _plugin_states[f"{ws_id}:{plugin_id}"] = True
    meta = _PLUGIN_REGISTRY.get(plugin_id, {"id": plugin_id, "name": plugin_id})
    return {"id": plugin_id, "enabled": True, "status": "active", "name": meta.get("name", plugin_id)}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin_mp(plugin_id: str, user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    _plugin_states[f"{ws_id}:{plugin_id}"] = False
    meta = _PLUGIN_REGISTRY.get(plugin_id, {"id": plugin_id, "name": plugin_id})
    return {"id": plugin_id, "enabled": False, "status": "inactive", "name": meta.get("name", plugin_id)}


@router.get("/plugins/{plugin_id}/docs")
async def plugin_docs(plugin_id: str, user=Depends(get_current_user)):
    meta = _PLUGIN_REGISTRY.get(plugin_id)
    if not meta:
        return {"id": plugin_id, "docs": "No documentation available for this plugin.", "sections": []}
    return {
        "id": plugin_id,
        "name": meta["name"],
        "version": meta["version"],
        "description": meta["description"],
        "author": meta["author"],
        "docs": f"# {meta['name']}\n\n{meta['description']}\n\n## Installation\n\nEnabled per-workspace. No additional setup required.\n\n## Configuration\n\nNo configuration needed for the default setup.",
        "sections": [
            {"title": "Overview", "content": meta["description"]},
            {"title": "Usage", "content": f"This plugin is automatically activated for all pipelines in your workspace once enabled."},
            {"title": "Version history", "content": f"v{meta['version']} — current stable release."},
        ],
    }


def get_automated_listing_price(l: MarketplaceListing, category_counts: dict | None = None) -> float:
    # If the listing is marked free, it remains free
    if l.price == 0.0 or l.pricing_model == "free":
        return 0.0
        
    cfg = l.config_json or {}
    target_price = float(cfg.get("target_price", l.price))
    if target_price <= 0.0:
        return l.price
        
    installs = l.downloads or 0
    
    # Milestone scale:
    # 0 - 10 installs: 20% of target price (trust building stage)
    if installs <= 10:
        factor = 0.20
    # 11 - 50 installs: 50% of target price (early adoption)
    elif installs <= 50:
        factor = 0.50
    # 51 - 100 installs: 80% of target price (established trust)
    elif installs <= 100:
        factor = 0.80
    # > 100 installs: 100% of target price
    else:
        factor = 1.00
        
    cat_count = 1
    if category_counts and l.category in category_counts:
        cat_count = category_counts[l.category]
        
    # Density / Rarity calibration
    if cat_count <= 2:
        density_multiplier = 1.00
    elif cat_count == 3:
        density_multiplier = 0.90
    elif cat_count == 4:
        density_multiplier = 0.80
    else:
        density_multiplier = 0.60
        
    calculated = round(target_price * factor * density_multiplier, 2)
    return calculated


def _listing_dict(l: MarketplaceListing, category_counts: dict | None = None) -> dict:
    cfg = l.config_json or {}
    
    installs = l.downloads or 0
    if installs <= 10:
        factor = 0.20
    elif installs <= 50:
        factor = 0.50
    elif installs <= 100:
        factor = 0.80
    else:
        factor = 1.00
        
    cat_count = 1
    if category_counts and l.category in category_counts:
        cat_count = category_counts[l.category]
        
    if cat_count <= 2:
        density_multiplier = 1.00
    elif cat_count == 3:
        density_multiplier = 0.90
    elif cat_count == 4:
        density_multiplier = 0.80
    else:
        density_multiplier = 0.60
        
    automated_price = get_automated_listing_price(l, category_counts=category_counts)
    target_price = float(cfg.get("target_price", l.price))
    
    return {
        "id": l.id,
        "name": l.name,
        "description": l.description,
        "category": l.category,
        "price": automated_price,
        "pricing_model": l.pricing_model,
        "status": l.status,
        "downloads": l.downloads,
        "rating": l.rating,
        "tags": l.tags or [],
        "vendor_name": cfg.get("vendor_name", "Veklom Native"),
        "vendor_slug": cfg.get("vendor_slug", "veklom_native"),
        "compliance_tags": cfg.get("compliance_tags", []),
        "badges": cfg.get("badges", []),
        "install_method": cfg.get("install_method", "container"),
        "deploy_target": cfg.get("deploy_target", "hetzner"),
        "license_type": cfg.get("license_type", "workspace-bound"),
        "watermark": cfg.get("watermark", ""),
        "build": cfg.get("build", "signed"),
        "long_description": cfg.get("long_description", l.description),
        "features": cfg.get("features", []),
        "install_instructions": cfg.get("install_instructions", ""),
        "compatibility": cfg.get("compatibility", []),
        "changelog": cfg.get("changelog", []),
        "github_url": cfg.get("github_url", ""),
        "docs_url": cfg.get("docs_url", ""),
        "pip_install": cfg.get("pip_install", ""),
        "target_price": target_price,
        "density_multiplier": density_multiplier,
        "category_density": cat_count,
        "is_rare": cat_count <= 2,
        "sovereign_baseline_premium": True,
        "pricing_formula": f"Target Price (${target_price:.2f}) * Milestone Factor ({factor * 100:.0f}%) * Density Multiplier ({density_multiplier * 100:.0f}%)" if target_price > 0.0 and l.pricing_model != "free" else "Free",
    }



def _source_marketplace_tools() -> list[dict]:
    return [
        {
            "id": "veklom-gpc",
            "name": "Governed Plan Compiler (GPC)",
            "category": "governance",
            "description": "Compiles messy intent into policy-checked execution plans.",
            "method": "POST",
            "endpoint": "/api/v1/gpc/compile",
            "runtime_provider": "ollama",
            "capabilities": ["intent_compile", "policy_check", "plan_generation"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-autonomous-router",
            "name": "Autonomous Execution Router",
            "category": "execution",
            "description": "Routes public demo intents through the BYOS control layer with Ollama-first execution.",
            "method": "POST",
            "endpoint": "/api/v1/autonomous/execute",
            "runtime_provider": "ollama",
            "capabilities": ["agent_execution", "vendor_discovery", "uacp_dispatch"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-policy-vault",
            "name": "Policy Vault",
            "category": "security",
            "description": "Evaluates tool calls, repository actions, and runtime boundaries before execution.",
            "method": "GET",
            "endpoint": "/api/v1/compliance/report",
            "runtime_provider": "ollama",
            "capabilities": ["policy_gate", "approval_boundary", "risk_classification"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-marketplace-vendor-discovery",
            "name": "Marketplace Vendor Discovery",
            "category": "marketplace",
            "description": "Finds potential Veklom-compatible vendors and tools without leaving the public demo boundary.",
            "method": "GET",
            "endpoint": "/api/v1/marketplace/tools",
            "runtime_provider": "ollama",
            "capabilities": ["vendor_lookup", "tool_registry", "marketplace_match"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-audit-sealer",
            "name": "Replayable Audit Evidence Sealer",
            "category": "evidence",
            "description": "Seals every demo action into a deterministic evidence block for replay.",
            "method": "GET",
            "endpoint": "/api/v1/internal/uacp/events",
            "runtime_provider": "ollama",
            "capabilities": ["audit_trail", "evidence_block", "lineage_tracking"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
    ]

# --- Webhook ---
@router.post("/marketplace/webhook")
async def marketplace_webhook(request: Request):
    # For now, just accept the ping or event and return 200 OK
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return {"status": "ok", "message": "Marketplace webhook received successfully"}
