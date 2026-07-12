from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .parser import extract_amphoteric_context

class AmphotericMiddleware(BaseHTTPMiddleware):
    """
    Middleware that parses inbound headers for W3C Trace and SPIFFE/Transport contexts,
    attaching them to the request state so downstream routers don't have to parse raw headers.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        headers_dict = dict(request.headers.items())
        
        trace_context, transport_context = extract_amphoteric_context(headers_dict)
        
        request.state.trace = trace_context
        request.state.transport = transport_context
        request.state.raw_headers = headers_dict
        
        response = await call_next(request)
        return response
