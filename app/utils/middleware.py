from typing import Iterable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings

STATE_CHANGING_METHODS: set[str] = {"POST", "PUT", "PATCH", "DELETE"}
_LOCALHOST_HOSTNAMES: set[str] = {"localhost", "127.0.0.1"}


class EnforceHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.enforce_https:
            return await call_next(request)
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        hostname = request.url.hostname
        allow_http_local = hostname in _LOCALHOST_HOSTNAMES
        if proto != "https" and not allow_http_local:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")
        response = await call_next(request)
        if proto == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={settings.hsts_max_age}; includeSubDomains"
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, exempt_paths: Iterable[str] | None = None):
        super().__init__(app)
        self.exempt_paths = set(exempt_paths or [])

    async def dispatch(self, request: Request, call_next):
        if request.method in STATE_CHANGING_METHODS and request.url.path not in self.exempt_paths:
            header_name = settings.csrf_header_name
            cookie_name = settings.csrf_cookie_name
            header_token = request.headers.get(header_name)
            cookie_token = request.cookies.get(cookie_name)
            if not header_token or not cookie_token or header_token != cookie_token:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF failed")
        return await call_next(request)
