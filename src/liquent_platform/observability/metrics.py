"""Bounded-cardinality Prometheus metrics for the control plane."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from liquent_platform import __version__


class ControlPlaneMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.requests = Counter(
            "http_requests_total",
            "Control-plane HTTP requests.",
            ("method", "route", "status"),
            namespace="liquent",
            registry=self.registry,
        )
        self.duration = Histogram(
            "http_request_duration_seconds",
            "Control-plane HTTP request duration.",
            ("method", "route"),
            namespace="liquent",
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )
        self.readiness = Gauge(
            "readiness",
            "One when the control plane is ready.",
            namespace="liquent",
            registry=self.registry,
        )
        self.build = Gauge(
            "build_info",
            "Static build metadata.",
            ("version",),
            namespace="liquent",
            registry=self.registry,
        )
        self.build.labels(version=__version__).set(1)
