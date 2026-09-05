from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.manifest_handoff_supervisor_candidate_composition import (
    CandidateManifestHandoffSupervisorGraph,
)
from liquent_platform.application.manifest_handoff_supervisor_process_composition import (
    ManifestHandoffSupervisorCandidateProcess,
    ManifestHandoffSupervisorCandidateReadinessProbe,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app


class RecordingClient:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def _settings(url: str) -> PlatformSettings:
    return PlatformSettings(
        _secrets_dir=None,
        database_url=url,
        manifest_handoff_supervisor_mode="candidate",
        manifest_handoff_supervisor_backend_instance_id="control-plane-a",
        manifest_handoff_supervisor_docker_socket=Path("/run/docker.sock"),
        manifest_handoff_supervisor_control_root=Path("/run/liquent/control-root"),
        manifest_handoff_supervisor_host_owner_uid=10001,
        manifest_handoff_supervisor_reader_gid=10002,
        manifest_handoff_supervisor_wrapper_uid=10002,
        manifest_handoff_supervisor_wrapper_gid=10002,
    )


def _process(client: RecordingClient | None = None):
    owner = client or RecordingClient()
    graph = object.__new__(CandidateManifestHandoffSupervisorGraph)
    process = ManifestHandoffSupervisorCandidateProcess(graph, owner)
    return process, ManifestHandoffSupervisorCandidateReadinessProbe(process), owner


def test_owned_process_contributes_not_ready_and_closes_once(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'factory.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    process, probe, owner = _process()
    app = create_app(
        _settings(url),
        database_engine=engine,
        manifest_handoff_supervisor_process=process,
        manifest_handoff_supervisor_readiness=probe,
        manifest_handoff_supervisor_process_owned=True,
    )
    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
            assert response.status_code == 503
            assert response.json()["reason"] == "manifest_handoff_supervisor_not_ready"
        assert owner.closed == 1
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "omitted",
    ("process", "readiness", "owned", "settings", "engine"),
)
def test_partial_supervisor_factory_group_fails_before_lifespan(
    omitted: str, tmp_path: Path
) -> None:
    url = f"sqlite:///{tmp_path / (omitted + '.db')}"
    engine = build_engine(url)
    process, probe, owner = _process()
    values = {
        "settings": _settings(url),
        "database_engine": engine,
        "manifest_handoff_supervisor_process": process,
        "manifest_handoff_supervisor_readiness": probe,
        "manifest_handoff_supervisor_process_owned": True,
    }
    key = {
        "process": "manifest_handoff_supervisor_process",
        "readiness": "manifest_handoff_supervisor_readiness",
        "owned": "manifest_handoff_supervisor_process_owned",
        "settings": "settings",
        "engine": "database_engine",
    }[omitted]
    if omitted == "settings":
        values[key] = PlatformSettings(_secrets_dir=None)
    elif omitted == "owned":
        values[key] = False
    else:
        values[key] = None
    try:
        with pytest.raises(ValueError, match="must be provided together"):
            create_app(**values)
        assert owner.closed == 0
    finally:
        process.close()
        engine.dispose()


def test_probe_must_belong_to_the_same_process(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'identity.db'}"
    engine = build_engine(url)
    process, _, owner = _process()
    other, other_probe, other_owner = _process()
    try:
        with pytest.raises(ValueError, match="must be provided together"):
            create_app(
                _settings(url), database_engine=engine,
                manifest_handoff_supervisor_process=process,
                manifest_handoff_supervisor_readiness=other_probe,
                manifest_handoff_supervisor_process_owned=True,
            )
        assert owner.closed == 0
        assert other_owner.closed == 0
    finally:
        process.close()
        other.close()
        engine.dispose()


def test_supervisor_group_cannot_mix_foreign_process_health(tmp_path: Path) -> None:
    from liquent_platform.application.health import ProcessHealth

    url = f"sqlite:///{tmp_path / 'health.db'}"
    engine = build_engine(url)
    process, probe, _ = _process()
    try:
        with pytest.raises(ValueError, match="must be provided together"):
            create_app(
                _settings(url), health=ProcessHealth(), database_engine=engine,
                manifest_handoff_supervisor_process=process,
                manifest_handoff_supervisor_readiness=probe,
                manifest_handoff_supervisor_process_owned=True,
            )
    finally:
        process.close()
        engine.dispose()


def test_followup_entrypoint_selection_remains_settings_gated() -> None:
    main = (
        Path(__file__).parents[1]
        / "src/liquent_platform/transport/http/main.py"
    ).read_text(encoding="utf-8")
    assert "if settings.manifest_handoff_supervisor_enabled:" in main
    assert "compose_manifest_handoff_supervisor_candidate_process" in main
    assert "manifest_handoff_supervisor_process=" in main
    compose = (
        Path(__file__).parents[1] / "operations/compose/compose.yaml"
    ).read_text(encoding="utf-8")
    assert "docker.sock" not in compose
