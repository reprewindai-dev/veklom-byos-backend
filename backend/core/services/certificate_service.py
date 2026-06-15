"""Certificate Service for signing and verifying execution certificates."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config.settings import settings
from backend.db.models.execution_certificate import ExecutionCertificate


class CertificateService:
    """Handles the creation, signature, and verification of execution certificates."""

    @staticmethod
    def create_jwt_token(payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a signed JWT token for the certificate."""
        to_encode = payload.copy()
        
        # Default expiration: 100 years if not specified (certificates are meant to be long-lived proof)
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=36500))
        to_encode.update({"exp": int(expire.timestamp())})
        
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Verify the JWT token and return the payload."""
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError as exc:
            raise ValueError("Invalid or expired certificate token") from exc

    @classmethod
    async def issue_execution_certificate(
        cls,
        db: AsyncSession,
        trace_id: str,
        genome_hash: str,
        input_hash: str,
        output_hash: str,
        watchtower_results: List[Dict[str, Any]],
        governance_tier: str,
        governance_overhead_ms: int,
        policy_version: Optional[str] = None,
        constitution_version: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> ExecutionCertificate:
        """
        Builds the certificate metadata, signs it into a JWT,
        saves the certificate record in the DB, and returns it.
        """
        # Create JWT payload
        payload = {
            "trace_id": trace_id,
            "genome_hash": genome_hash,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "watchtower_results": watchtower_results,
            "governance_tier": governance_tier,
            "governance_overhead_ms": governance_overhead_ms,
            "policy_version": policy_version,
            "constitution_version": constitution_version,
            "issued_at": int(datetime.now(timezone.utc).timestamp())
        }

        # Sign JWT
        certificate_jwt = cls.create_jwt_token(payload, expires_delta=expires_delta)

        # Parse expiry date
        expires_at = None
        if expires_delta:
            expires_at = datetime.utcnow() + expires_delta

        # Check if one already exists for this trace_id
        query = select(ExecutionCertificate).where(ExecutionCertificate.trace_id == trace_id)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.genome_hash = genome_hash
            existing.input_hash = input_hash
            existing.output_hash = output_hash
            existing.watchtower_results = watchtower_results
            existing.governance_tier = governance_tier
            existing.governance_overhead_ms = governance_overhead_ms
            existing.policy_version = policy_version
            existing.constitution_version = constitution_version
            existing.certificate_jwt = certificate_jwt
            existing.expires_at = expires_at
            
            await db.commit()
            await db.refresh(existing)
            return existing

        # Save to DB
        cert = ExecutionCertificate(
            trace_id=trace_id,
            genome_hash=genome_hash,
            input_hash=input_hash,
            output_hash=output_hash,
            watchtower_results=watchtower_results,
            governance_tier=governance_tier,
            governance_overhead_ms=governance_overhead_ms,
            policy_version=policy_version,
            constitution_version=constitution_version,
            certificate_jwt=certificate_jwt,
            expires_at=expires_at
        )

        db.add(cert)
        await db.commit()
        await db.refresh(cert)
        return cert

    @classmethod
    async def verify_certificate_by_trace(cls, db: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """Retrieve certificate from DB and verify its signed JWT contents."""
        query = select(ExecutionCertificate).where(ExecutionCertificate.trace_id == trace_id)
        result = await db.execute(query)
        cert = result.scalar_one_or_none()
        
        if not cert:
            raise ValueError(f"No execution certificate found for trace_id: {trace_id}")

        # Decode and verify JWT
        decoded_payload = cls.verify_jwt_token(cert.certificate_jwt)
        
        # Verify hashes match DB
        if decoded_payload.get("genome_hash") != cert.genome_hash or decoded_payload.get("trace_id") != cert.trace_id:
            raise ValueError("Certificate payload mismatch with database record")

        return {
            "verified": True,
            "cert_id": cert.id,
            "trace_id": cert.trace_id,
            "genome_hash": cert.genome_hash,
            "input_hash": cert.input_hash,
            "output_hash": cert.output_hash,
            "governance_tier": cert.governance_tier,
            "watchtower_results": cert.watchtower_results,
            "governance_overhead_ms": cert.governance_overhead_ms,
            "issued_at": cert.issued_at,
            "expires_at": cert.expires_at
        }
