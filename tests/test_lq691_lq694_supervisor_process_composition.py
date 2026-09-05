from pathlib import Path
import os

import pytest

import liquent_platform.application.manifest_handoff_supervisor_process_composition as composition
from liquent_platform.application.manifest_handoff_supervisor_candidate_composition import (
    CandidateManifestHandoffSupervisorGraph,
)
from liquent_platform.application.manifest_handoff_supervisor_process_composition import (
    ManifestHandoffSupervisorCandidateProcess,
    compose_manifest_handoff_supervisor_candidate_process,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


def _settings(**changes: object) -> PlatformSettings:
    owner = os.geteuid()
    wrapper = owner + 1 if owner < 2_147_483_647 else owner - 1
    values: dict[str, object] = {
        "database_url": "sqlite://",
        "manifest_handoff_supervisor_mode": "candidate",
        "manifest_handoff_supervisor_backend_instance_id": "control-plane-a",
        "manifest_handoff_supervisor_docker_socket": Path("/run/docker.sock"),
        "manifest_handoff_supervisor_control_root": Path("/run/liquent/control-root"),
        "manifest_handoff_supervisor_host_owner_uid": owner,
        "manifest_handoff_supervisor_reader_gid": 10002,
        "manifest_handoff_supervisor_wrapper_uid": wrapper,
        "manifest_handoff_supervisor_wrapper_gid": 10002,
    }
    values.update(changes)
    return PlatformSettings(_secrets_dir=None, **values)


def test_complete_settings_compose_one_inert_exclusive_candidate() -> None:
    engine = build_engine("sqlite://")
    try:
        process = compose_manifest_handoff_supervisor_candidate_process(
            settings=_settings(),
            database_engine=engine,
            backend_instance_id=ManifestHandoffSupervisorBackendInstanceId("lq691"),
        )
        assert type(process) is ManifestHandoffSupervisorCandidateProcess
        assert type(process.graph) is CandidateManifestHandoffSupervisorGraph
        assert process.graph.production_ready is False
        assert process.production_ready is False
        assert "docker.sock" not in repr(process)
        process.close()
        process.close()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "change",
    (
        {"settings": PlatformSettings(_secrets_dir=None)},
        {"database_engine": object()},
        {"backend_instance_id": object()},
    ),
)
def test_incomplete_process_dependencies_fail_before_io(change: dict[str, object]) -> None:
    engine = build_engine("sqlite://")
    values: dict[str, object] = {
        "settings": _settings(),
        "database_engine": engine,
        "backend_instance_id": ManifestHandoffSupervisorBackendInstanceId("lq692"),
    }
    values.update(change)
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
            compose_manifest_handoff_supervisor_candidate_process(**values)
        assert str(caught.value) == "manifest_handoff_registry_unavailable"
    finally:
        engine.dispose()


def test_composition_failure_closes_only_the_created_client(monkeypatch) -> None:
    class Client:
        closed = 0

        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            self.closed += 1

    client = Client()
    monkeypatch.setattr(composition, "LocalDockerEngineHttpClient", lambda *a, **k: client)
    monkeypatch.setattr(
        composition,
        "compose_candidate_manifest_handoff_supervisor_graph",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("composition")),
    )
    engine = build_engine("sqlite://")
    try:
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            compose_manifest_handoff_supervisor_candidate_process(
                settings=_settings(), database_engine=engine,
                backend_instance_id=ManifestHandoffSupervisorBackendInstanceId("lq693"),
            )
        assert client.closed == 1
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    finally:
        engine.dispose()


def test_process_close_is_detail_free_and_does_not_claim_readiness() -> None:
    class BrokenClient:
        def close(self):
            raise RuntimeError("private socket detail")

    graph = object.__new__(CandidateManifestHandoffSupervisorGraph)
    process = ManifestHandoffSupervisorCandidateProcess(graph, BrokenClient())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        process.close()
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "private socket detail" not in str(caught.value)
    process.close()


def test_composition_source_has_no_appfactory_deployment_or_compatibility_graph() -> None:
    source = Path(composition.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "create_app", "compose.yaml", "os.environ",
        "compose_persistent_manifest_handoff_supervisor_service",
        "PersistentManifestHandoffSupervisorService",
        "database_engine.dispose",
    ):
        assert forbidden not in source
