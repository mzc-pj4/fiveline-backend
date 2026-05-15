import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import log_access, log_service_event


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log_access(
                api_path=request.url.path,
                method=request.method,
                status_code=500,
                response_time_ms=elapsed_ms,
                trace_id=trace_id,
            )
            log_service_event(
                "API_ERROR", api_path=request.url.path, trace_id=trace_id,
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log_access(
            api_path=request.url.path,
            method=request.method,
            status_code=status_code,
            response_time_ms=elapsed_ms,
            trace_id=trace_id,
        )
        if elapsed_ms >= 1500:
            log_service_event(
                "SLOW_RESPONSE",
                api_path=request.url.path,
                response_time_ms=elapsed_ms,
                trace_id=trace_id,
            )
        response.headers["x-trace-id"] = trace_id
        return response
