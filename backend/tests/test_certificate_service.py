"""Tests for Certificate Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.services.certificate_service import CertificateService
from backend.db.models.execution_certificate import ExecutionCertificate


@pytest.mark.asyncio
async def test_issue_execution_certificate():
    db = AsyncMock()
    
    # Mock database trace lookups
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res
    
    trace_id = "trace_xyz123"
    genome_hash = "merkle_root_hash"
    input_hash = "input_data_hash"
    output_hash = "output_data_hash"
    watchtower_results = [{"name": "pii", "passed": True}]
    tier = "T1"
    
    cert = await CertificateService.issue_execution_certificate(
        db=db,
        trace_id=trace_id,
        genome_hash=genome_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        watchtower_results=watchtower_results,
        governance_tier=tier,
        governance_overhead_ms=120,
        policy_version="1.0.0",
        constitution_version="1.0.0"
    )
    
    assert cert.trace_id == trace_id
    assert cert.genome_hash == genome_hash
    assert cert.governance_tier == tier
    assert cert.certificate_jwt is not None
    
    # Verify signature matches
    decoded = CertificateService.verify_jwt_token(cert.certificate_jwt)
    assert decoded["trace_id"] == trace_id
    assert decoded["genome_hash"] == genome_hash
    assert decoded["governance_tier"] == tier


@pytest.mark.asyncio
async def test_verify_certificate_by_trace():
    db = AsyncMock()
    
    # Create fake certificate
    cert = ExecutionCertificate(
        id="cert_uuid",
        trace_id="trace_123",
        genome_hash="genome_123",
        input_hash="input_123",
        output_hash="output_123",
        watchtower_results=[],
        governance_tier="T0",
        governance_overhead_ms=50,
        policy_version="1.0.0",
        constitution_version="1.0.0"
    )
    
    payload = {
        "trace_id": "trace_123",
        "genome_hash": "genome_123",
        "input_hash": "input_123",
        "output_hash": "output_123",
        "watchtower_results": [],
        "governance_tier": "T0",
        "governance_overhead_ms": 50,
        "policy_version": "1.0.0",
        "constitution_version": "1.0.0"
    }
    cert.certificate_jwt = CertificateService.create_jwt_token(payload)
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = cert
    db.execute.return_value = mock_res
    
    verified_data = await CertificateService.verify_certificate_by_trace(db, "trace_123")
    
    assert verified_data["verified"] is True
    assert verified_data["trace_id"] == "trace_123"
    assert verified_data["governance_tier"] == "T0"
