import hashlib

from fastapi import HTTPException, Request, status


async def require_payment_proof(request: Request) -> dict:
    """Require proof that the x402 middleware completed payment verification.

    Caller-controlled headers are metadata only; they are never accepted as proof
    without the middleware's verified request state.
    """
    if not getattr(request.state, "x402_verified", False):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Verified payment is required for governed execution.",
        )

    proof_header = (
        request.headers.get("x-payment")
        or request.headers.get("payment-signature")
        or request.headers.get("x-payment-proof")
    )
    proof_hash = getattr(request.state, "x402_proof_hash", None)
    return {
        "payment_proof_hash": proof_hash or hashlib.sha256((proof_header or "").encode()).hexdigest(),
        "verified": True,
    }
