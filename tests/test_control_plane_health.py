from fastapi.testclient import TestClient

from liquent_platform.application.health import ProcessHealth
from liquent_platform.configuration import PlatformSettings
from liquent_platform.transport.http.app import create_app


def _app(health: ProcessHealth | None = None):
    return create_app(PlatformSettings(_secrets_dir=None), health)


def test_liveness_is_local_and_independent_of_readiness() -> None:
    health = ProcessHealth()
    with TestClient(_app(health)) as client:
        health.mark_stopping()
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "liquent-control-plane"}


def test_readiness_is_ready_after_successful_startup() -> None:
    with TestClient(_app()) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "liquent-control-plane",
        "reason": "ready",
    }


def test_readiness_returns_503_with_machine_readable_reason() -> None:
    health = ProcessHealth()
    with TestClient(_app(health)) as client:
        health.mark_stopping()
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "liquent-control-plane",
        "reason": "startup_incomplete",
    }


def test_product_api_and_interactive_docs_are_not_exposed() -> None:
    with TestClient(_app()) as client:
        assert client.get("/api/v1").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
