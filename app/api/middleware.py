"""HTTP middleware for request tracing and operational logging."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.logging_config import request_id_var


logger = logging.getLogger("sellerops.api.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request completed",
                extra={
                    "sellerops_method": request.method,
                    "sellerops_path": request.url.path,
                    "sellerops_status_code": status_code,
                    "sellerops_duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)
