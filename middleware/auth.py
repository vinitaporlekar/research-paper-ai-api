from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for docs, health check, and OPTIONS (CORS preflight)
        skip_paths = ["/", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in skip_paths or request.method == "OPTIONS":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            return JSONResponse(
                status_code=500,
                content={"detail": "API_KEY not configured on server"}
            )

        if api_key != expected_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)