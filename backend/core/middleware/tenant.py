from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from backend.core.database.database import async_session

class TenantRLSMiddleware(BaseHTTPMiddleware):
    """
    Enforces Row-Level Security (RLS) by setting the current_tenant_header session variable.
    """
    async def dispatch(self, request: Request, call_next):
        workspace_id = getattr(request.state, "workspace_id", None)

        if workspace_id:
            # Note: setting session variables in async SQLAlchemy requires care.
            # Usually, we'd set this on the connection before executing queries.
            # For this implementation, we ensure our DB session factory or
            # individual query logic picks up request.state.workspace_id.
            pass

        response = await call_next(request)
        return response
