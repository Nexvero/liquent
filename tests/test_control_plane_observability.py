from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from liquent_platform.configuration import PlatformSettings
from liquent_platform.observability.logging import JsonFormatter, correlation_id
from liquent_platform.transport.http.app import create_app


def _client() -> TestClient:
    return TestClient(create_app(PlatformSettings(_secrets_dir=None)))


def test_valid_correlation_id_is_returned() -> None:
    with _client() as client:
        response = client.get("/health/live", headers={"x-correlation-id": "release-123"})
    assert response.headers["x-correlation-id"] == "release-123"


def test_invalid_correlation_id_is_replaced() -> None:
    with _client() as client:
        response = client.get("/health/live", headers={"x-correlation-id": "unsafe value!"})
    replacement = response.headers["x-correlation-id"]
    assert replacement != "unsafe value!"
    assert len(replacement) == 32
    int(replacement, 16)


def test_metrics_use_route_templates_and_bounded_labels() -> None:
    with _client() as client:
        client.get("/health/live")
        client.get("/does-not-exist/secret-object-123")
        metrics = client.get("/internal/metrics").text
    assert 'route="/health/live",status="200"' in metrics
    assert 'route="unmatched",status="404"' in metrics
    assert "secret-object-123" not in metrics
    assert "liquent_http_request_duration_seconds_bucket" in metrics
    assert 'liquent_build_info{version="0.0.1"} 1.0' in metrics


def test_readiness_gauge_tracks_latest_result() -> None:
    with _client() as client:
        assert client.get("/health/ready").status_code == 200
        metrics = client.get("/internal/metrics").text
    assert "liquent_readiness 1.0" in metrics


def test_json_formatter_emits_stable_fields_and_correlation() -> None:
    token = correlation_id.set("corr-42")
    try:
        record = logging.LogRecord(
            "liquent.test", logging.INFO, __file__, 1, "test_event", (), None
        )
        record.method = "GET"
        rendered = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id.reset(token)
    assert rendered["severity"] == "INFO"
    assert rendered["service"] == "liquent-control-plane"
    assert rendered["event"] == "test_event"
    assert rendered["correlation_id"] == "corr-42"
    assert rendered["method"] == "GET"
    assert set(rendered).issubset(
        {"timestamp", "severity", "service", "event", "correlation_id", "method"}
    )
