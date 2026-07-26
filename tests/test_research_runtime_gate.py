from pathlib import Path

from fastapi.testclient import TestClient

from liquent_platform.configuration import PlatformSettings
from liquent_platform.transport.http.main import build_app


def test_default_runtime_does_not_register_research_start() -> None:
    app = build_app(PlatformSettings(_secrets_dir=None))

    with TestClient(app) as client:
        response = client.post("/v1/research/jobs", json={})

    assert response.status_code == 404


def test_configured_existing_data_root_registers_research_start(tmp_path: Path) -> None:
    app = build_app(
        PlatformSettings(_secrets_dir=None, research_data_root=tmp_path)
    )

    with TestClient(app) as client:
        response = client.post("/v1/research/jobs", json={})

    assert response.status_code == 422


def test_missing_data_root_fails_during_app_build(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    try:
        build_app(PlatformSettings(_secrets_dir=None, research_data_root=missing))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing research data root must fail startup")
