from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import app
from app.logging import Ansi
from app.logging import log
from app.logging import magnitude_fmt_time


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.perf_counter_ns()
        response = await call_next(request)
        end_time = time.perf_counter_ns()

        time_elapsed = end_time - start_time

        col = Ansi.LGREEN if response.status_code < 400 else Ansi.LRED

        url = f"{request.headers['host']}{request['path']}"

        log(
            f"[{request.method}] {response.status_code} {url}{Ansi.RESET!r} | {Ansi.LBLUE!r}Request took: {magnitude_fmt_time(time_elapsed)}",
            col,
        )

        response.headers["process-time"] = str(round(time_elapsed) / 1e6)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, *args, max_requests_per_second: int = 30, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_requests_per_second = max_requests_per_second
        self.last_access_time = 0
        self.tokens = 0

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        host = request.headers.get("host", "")
        if not host.startswith("api."):
            # Skip rate limiting for non-"api" subdomain requests
            return await call_next(request)

        current_time = time.time()

        # Refill tokens
        elapsed_time = current_time - self.last_access_time
        tokens_to_add = int(elapsed_time * self.max_requests_per_second)
        self.tokens = min(self.tokens + tokens_to_add, self.max_requests_per_second)
        self.last_access_time = current_time

        # Check if enough tokens are available
        if self.tokens < 1:
            ip = app.state.services.ip_resolver.get_ip(request.headers)
            url = request.url.path
            print(f"Rate Limit Exceeded - IP: {ip}, Endpoint: {url}")
            return Response("Too Many Requests", status_code=429)

        # Consume a token
        self.tokens -= 1

        # Call the next middleware
        response = await call_next(request)

        return response