"""Security middleware for HTTP headers."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        # Extract environment boundary (default to sandbox for safety)
        env = request.headers.get("x-veklom-environment", "sandbox").lower()
        if env not in ("sandbox", "production"):
            env = "sandbox"
        request.state.environment = env

        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https://api.stripe.com https://veklom.com https://api.veklom.com; "
            "frame-src 'self' https://lockerphycer.veklom.com https://uacpv3.onrender.com https://js.stripe.com; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        
        # Strict Transport Security (only in production and never on localhost)
        from backend.core.config.settings import settings
        hostname = (request.url.hostname or "").lower()
        if settings.APP_ENV == "production" and hostname not in ("localhost", "127.0.0.1", "0.0.0.0"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # X-Frame-Options — SAMEORIGIN allows veklom.com to embed its own pages (terminal, irongrid etc.)
        # Skip for routes that are meant to be iframed within the landing page
        path = request.url.path
        iframe_routes = ("/terminal", "/repogate", "/irongrid", "/command-center", "/gpc", "/gpc-engine", "/workspace")
        if not any(path.startswith(r) for r in iframe_routes):
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        # else: no X-Frame-Options header — allows veklom.com to iframe these pages
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Robots: keep ONLY the temporary staging preview UI out of search engines.
        # This is route-specific by design — it must NOT be applied globally.
        # The public product site (/, /pricing, /marketplace, /docs), x402 discovery
        # (/.well-known/x402.json) and all /api/v1/* routes stay fully indexable.
        if path.startswith("/control-plane-next"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), "
            "usb=(), magnetometer=(), gyroscope=()"
        )

        # Remove server identification header
        try:
            del response.headers["server"]
        except (KeyError, AttributeError):
            pass
        try:
            del response.headers["Server"]
        except (KeyError, AttributeError):
            pass

        return response
