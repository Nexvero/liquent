"""Minimal structured logging with request correlation context."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
import sys


correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    """Emit a stable, single-line JSON event without arbitrary record fields."""

    _OPTIONAL_FIELDS = ("method", "route", "status_code", "duration_ms", "reason")

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, str | int | float] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": "liquent-control-plane",
            "event": record.getMessage(),
        }
        request_id = correlation_id.get()
        if request_id is not None:
            event["correlation_id"] = request_id
        for field in self._OPTIONAL_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (str, int, float)):
                event[field] = value
        if record.exc_info:
            event["exception_type"] = record.exc_info[0].__name__
        return json.dumps(event, separators=(",", ":"), ensure_ascii=True)


def configure_logging(level: str, log_format: str) -> None:
    """Replace root handlers once at process start."""

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
