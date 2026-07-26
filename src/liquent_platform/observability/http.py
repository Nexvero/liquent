"""ASGI observability middleware with validated correlation IDs."""

from __future__ import annotations

import logging
import re
from time import monotonic
from typing import Any
from uuid import uuid4

from liquent_platform.observability.logging import correlation_id
from liquent_platform.observability.metrics import ControlPlaneMetrics


_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_LOGGER = logging.getLogger("liquent.http")


def accepted_correlation_id(headers: list[tuple[bytes, bytes]]) -> str:
    for name, value in headers:
        if name.lower() == b"x-correlation-id":
            candidate = value.decode("ascii", errors="ignore")
            if _CORRELATION_ID.fullmatch(candidate):
                return candidate
            break
    return uuid4().hex


class ObservabilityMiddleware:
    def __init__(self, app: Any, metrics: ControlPlaneMetrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = accepted_correlation_id(scope.get("headers", []))
        token = correlation_id.set(request_id)
        started = monotonic()
        status_code = 500

        async def observed_send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-correlation-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except Exception:
            _LOGGER.exception("http_request_failed")
            raise
        finally:
            duration = monotonic() - started
            route_object = scope.get("route")
            route = getattr(route_object, "path", "unmatched")
            method = str(scope.get("method", "UNKNOWN"))
            self.metrics.requests.labels(
                method=method,
                route=route,
                status=str(status_code),
            ).inc()
            self.metrics.duration.labels(method=method, route=route).observe(duration)
            _LOGGER.info(
                "http_request_completed",
                extra={
                    "method": method,
                    "route": route,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 3),
                },
            )
            correlation_id.reset(token)
