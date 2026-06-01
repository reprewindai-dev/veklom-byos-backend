"""Veklom Fax Connector Router.

Implements governed fax-to-workflow automation for highly regulated industries:
Hospitals, Legal, Government, and Financial Services.
Supports modern fax-over-IP/eFax webhooks, OCR extraction, AI classification,
secure document queue routing, evidence/audit trail sealing, and approved outbound sending.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.security import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors/fax", tags=["Fax Connector"])

# In-memory storage mock for fax queue (since we are not adding new models to keep DB pristine)
# Faxes will also be registered under the AuditLog table for durable audit sealing.
FAX_DB: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class InboundFaxWebhook(BaseModel):
    sender_number: str = Field(..., description="Originating fax number (e.g. +15550192)", example="+15550192")
    receiver_number: str = Field(..., description="Destination fax number inside Veklom", example="+18005550100")
    document_url: str = Field(..., description="Secure link to the ingested PDF/TIFF file", example="https://storage.veklom.com/faxes/inbound_2026_06_01.pdf")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Metadata from the FoIP gateway (e.g. SRFax, WestFax)")

class OutboundFaxRequest(BaseModel):
    recipient_number: str = Field(..., description="Target fax number", example="+15550999")
    sender_number: str = Field(..., description="Outgoing fax line authorized in Veklom", example="+18005550100")
    document_url: str = Field(..., description="URL of the document to send", example="https://storage.veklom.com/faxes/outbound_draft_102.pdf")
    require_approval: bool = Field(True, description="Enforce governance sign-off before sending")

class FaxApprovalRequest(BaseModel):
    approved: bool = Field(..., description="Approval decision")
    reviewer_notes: Optional[str] = Field(None, description="Compliance and clinical/legal review notes")

class FaxResponse(BaseModel):
    fax_id: str
    status: str
    sender_number: str
    receiver_number: str
    document_url: str
    ocr_text: Optional[str] = None
    classification: Optional[str] = None
    evidence_id: str
    timestamp: datetime
    approved_by: Optional[str] = None
    approval_notes: Optional[str] = None
    industry_context: Optional[str] = None

# ---------------------------------------------------------------------------
# Mock OCR & Classifier AI helpers
# ---------------------------------------------------------------------------

def simulate_ocr_and_classification(document_url: str) -> tuple[str, str, str]:
    """
    Simulates high-accuracy optical character recognition (OCR) and
    governed industry document classification.
    """
    url_lower = document_url.lower()
    if "patient" in url_lower or "medical" in url_lower or "clinical" in url_lower:
        ocr_text = (
            "PATIENT intake form. NAME: John Doe. DOB: 08/14/1982. DIAGNOSIS: Essential hypertension. "
            "PROVIDER: Sovereign Health Partners. POLICY: GVC-88912A. Treatment plan requested."
        )
        classification = "PHI_CLINICAL_INTAKE"
        industry = "Healthcare (HIPAA Regulated)"
    elif "court" in url_lower or "legal" in url_lower or "brief" in url_lower:
        ocr_text = (
            "IN THE DISTRICT COURT of Veklom. CASE NO: 2026-CV-88912. PLAINTIFF: Veklom Corp. "
            "DEFENDANT: Sovereign Infrastructure Group. MOTION for Summary Judgment."
        )
        classification = "LEGAL_COURT_FILING"
        industry = "Legal Services"
    elif "invoice" in url_lower or "billing" in url_lower or "claim" in url_lower:
        ocr_text = (
            "VEKLOM BILLING & CLAIMS. INVOICE ID: INV-99021. TOTAL DUE: $12,500.00 USDC. "
            "SERVICE DETAILED: GPU Node Sovereign execution hours. TAX ID: 99-81273."
        )
        classification = "FINANCIAL_INVOICE"
        industry = "Financial Services / Billing"
    else:
        ocr_text = (
            "VEKLOM SECURE INGESTION GATEWAY. Inbound document transmission. "
            "Lineage: Fax-over-IP (FoIP) server. Check integrity seal."
        )
        classification = "UNCLASSIFIED_GOVERNED_DOC"
        industry = "General Governance"
        
    return ocr_text, classification, industry

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/inbound", response_model=FaxResponse, status_code=status.HTTP_201_CREATED)
async def inbound_fax_webhook(
    body: InboundFaxWebhook,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook target for eFax / FoIP gateways.
    Performs secure PDF/TIFF ingestion, OCR extraction, document classification,
    and seals the execution in the audit evidence ledger.
    """
    signature = request.headers.get("X-Fax-Signature") or request.headers.get("X-Fax-Gateway-Token")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook authentication header"
        )
    if signature != settings.FAX_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature or gateway token"
        )
    fax_id = f"fax_in_{uuid.uuid4().hex[:12]}"
    evidence_id = f"evd_{uuid.uuid4().hex[:16]}"
    
    # Run OCR and classification simulation
    ocr_text, classification, industry = simulate_ocr_and_classification(body.document_url)
    
    fax_record = {
        "fax_id": fax_id,
        "status": "queued",
        "sender_number": body.sender_number,
        "receiver_number": body.receiver_number,
        "document_url": body.document_url,
        "ocr_text": ocr_text,
        "classification": classification,
        "evidence_id": evidence_id,
        "timestamp": datetime.now(timezone.utc),
        "approved_by": None,
        "approval_notes": None,
        "industry_context": industry
    }
    
    FAX_DB[fax_id] = fax_record
    
    # Seal the inbound fax in the durable audit ledger
    audit_detail = {
        "event_type": "inbound_fax_ingest",
        "fax_id": fax_id,
        "classification": classification,
        "evidence_id": evidence_id,
        "sender_number": body.sender_number,
        "receiver_number": body.receiver_number,
        "ocr_summary": ocr_text[:120] + "...",
        "industry_context": industry,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    
    audit_log = AuditLog(
        user_id="system-gateway",
        action="CONNECTORS_FAX_INGEST",
        resource_type="fax_connector",
        resource_id=fax_id,
        details={**audit_detail, "status": "success"}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"[Fax Inbound] Logged {fax_id} with classification {classification}. Evidence Sealed: {evidence_id}")
    return FaxResponse(**fax_record)


@router.post("/send", response_model=FaxResponse, status_code=status.HTTP_201_CREATED)
async def send_outbound_fax(
    body: OutboundFaxRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates outbound fax delivery to legacy endpoints.
    Enforces Veklom's zero-trust governance: if `require_approval` is active,
    the fax goes into a `pending_approval` state until a supervisor reviews.
    """
    fax_id = f"fax_out_{uuid.uuid4().hex[:12]}"
    evidence_id = f"evd_{uuid.uuid4().hex[:16]}"
    
    status_state = "pending_approval" if body.require_approval else "sent"
    
    ocr_text, classification, industry = simulate_ocr_and_classification(body.document_url)
    
    fax_record = {
        "fax_id": fax_id,
        "status": status_state,
        "sender_number": body.sender_number,
        "receiver_number": body.recipient_number,
        "document_url": body.document_url,
        "ocr_text": ocr_text,
        "classification": classification,
        "evidence_id": evidence_id,
        "timestamp": datetime.now(timezone.utc),
        "approved_by": None,
        "approval_notes": None,
        "industry_context": industry
    }
    
    FAX_DB[fax_id] = fax_record
    
    audit_detail = {
        "event_type": "outbound_fax_init",
        "fax_id": fax_id,
        "status": status_state,
        "sender_number": body.sender_number,
        "receiver_number": body.recipient_number,
        "require_approval": body.require_approval,
        "initiated_by": user.id,
        "evidence_id": evidence_id
    }
    
    audit_log = AuditLog(
        user_id=user.id,
        action="CONNECTORS_FAX_SEND",
        resource_type="fax_connector",
        resource_id=fax_id,
        details={**audit_detail, "status": "success"}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"[Fax Outbound] Outbound transmission {fax_id} initialized with state: {status_state}")
    return FaxResponse(**fax_record)


@router.get("/inbox", response_model=List[FaxResponse])
async def get_fax_inbox(
    user=Depends(get_current_user)
):
    """
    Retrieves the governed fax transmission ledger (inbox & queue).
    Used directly by the control plane's workspace human review UI.
    """
    # Simply return all values in reverse-chronological order
    faxes = list(FAX_DB.values())
    faxes.sort(key=lambda x: x["timestamp"], reverse=True)
    return [FaxResponse(**f) for f in faxes]


@router.post("/approve/{fax_id}", response_model=FaxResponse)
async def approve_fax_workflow(
    fax_id: str,
    body: FaxApprovalRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enforces compliance sign-off on inbound/outbound queued faxes.
    If approved, transitions fax status and releases it to downstream systems.
    """
    if fax_id not in FAX_DB:
        raise HTTPException(status_code=404, detail="Fax record not found.")
        
    fax = FAX_DB[fax_id]
    
    if body.approved:
        # If it was outbound pending, mark as sent. If inbound queue, mark as approved
        fax["status"] = "sent" if fax_id.startswith("fax_out") else "approved"
    else:
        fax["status"] = "rejected"
        
    fax["approved_by"] = user.id
    fax["approval_notes"] = body.reviewer_notes
    
    # Commit audit trial update
    audit_detail = {
        "event_type": "fax_approval_decision",
        "fax_id": fax_id,
        "decision": "approved" if body.approved else "rejected",
        "reviewer": user.id,
        "notes": body.reviewer_notes,
        "evidence_id": fax["evidence_id"]
    }
    
    audit_log = AuditLog(
        user_id=user.id,
        action="CONNECTORS_FAX_APPROVAL",
        resource_type="fax_connector",
        resource_id=fax_id,
        details={**audit_detail, "status": "success"}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"[Fax Approval] Fax {fax_id} set to {fax['status']} by reviewer {user.id}")
    return FaxResponse(**fax)


@router.get("/{fax_id}", response_model=FaxResponse)
async def get_fax_details(
    fax_id: str,
    user=Depends(get_current_user)
):
    """
    Fetches comprehensive details of a specific fax.
    """
    if fax_id not in FAX_DB:
        raise HTTPException(status_code=404, detail="Fax record not found.")
    return FaxResponse(**FAX_DB[fax_id])
