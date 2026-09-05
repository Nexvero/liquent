from pathlib import Path

import pytest

import liquent_platform.transport.http.main as runtime
from liquent_platform.configuration import PlatformSettings


def _settings() -> PlatformSettings:
    return PlatformSettings(
        _secrets_dir=None,
        database_url="sqlite://",
        manifest_handoff_supervisor_mode="candidate",
        manifest_handoff_supervisor_backend_instance_id="control-plane-a",
        manifest_handoff_supervisor_docker_socket=Path("/run/docker.sock"),
        manifest_handoff_supervisor_control_root=Path("/run/liquent/control-root"),
        manifest_handoff_supervisor_host_owner_uid=10001,
        manifest_handoff_supervisor_reader_gid=10002,
        manifest_handoff_supervisor_wrapper_uid=10002,
        manifest_handoff_supervisor_wrapper_gid=10002,
    )


class Engine:
    def __init__(self) -> None:
        self.disposed = 0

    def dispose(self) -> None:
        self.disposed += 1


class Process:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class Probe:
    def __init__(self, process) -> None:
        self.process = process


def test_entrypoint_binds_one_engine_backend_process_probe_and_ownership(monkeypatch) -> None:
    engine = Engine()
    process = Process()
    seen: dict[str, object] = {}
    sentinel = object()
    monkeypatch.setattr(runtime, "build_engine", lambda url: engine)
    monkeypatch.setattr(
        runtime, "ManifestHandoffSupervisorCandidateReadinessProbe", Probe
    )

    def compose(**values):
        seen["composition"] = values
        return process

    def factory(settings, **values):
        seen["factory"] = values
        return sentinel

    monkeypatch.setattr(runtime, "compose_manifest_handoff_supervisor_candidate_process", compose)
    monkeypatch.setattr(runtime, "create_app", factory)

    assert runtime.build_app(_settings()) is sentinel
    composition = seen["composition"]
    factory_values = seen["factory"]
    assert composition["database_engine"] is engine
    assert composition["backend_instance_id"].value == "control-plane-a"
    assert factory_values["database_engine"] is engine
    assert factory_values["database_engine_owned"] is True
    assert factory_values["manifest_handoff_supervisor_process"] is process
    assert factory_values["manifest_handoff_supervisor_process_owned"] is True
    assert factory_values["manifest_handoff_supervisor_readiness"].process is process
    assert engine.disposed == 0
    assert process.closed == 0


def test_composition_failure_disposes_engine_without_factory(monkeypatch) -> None:
    engine = Engine()
    called = False
    monkeypatch.setattr(runtime, "build_engine", lambda url: engine)
    monkeypatch.setattr(
        runtime,
        "compose_manifest_handoff_supervisor_candidate_process",
        lambda **values: (_ for _ in ()).throw(RuntimeError("composition")),
    )

    def factory(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(runtime, "create_app", factory)
    with pytest.raises(RuntimeError, match="composition"):
        runtime.build_app(_settings())
    assert engine.disposed == 1
    assert called is False


def test_factory_failure_closes_process_then_disposes_engine(monkeypatch) -> None:
    engine = Engine()
    process = Process()
    monkeypatch.setattr(runtime, "build_engine", lambda url: engine)
    monkeypatch.setattr(
        runtime, "ManifestHandoffSupervisorCandidateReadinessProbe", Probe
    )
    monkeypatch.setattr(
        runtime, "compose_manifest_handoff_supervisor_candidate_process",
        lambda **values: process,
    )
    monkeypatch.setattr(
        runtime, "create_app",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("factory")),
    )
    with pytest.raises(RuntimeError, match="factory"):
        runtime.build_app(_settings())
    assert process.closed == 1
    assert engine.disposed == 1


def test_closed_supervisor_settings_preserve_existing_entrypoint_shape(monkeypatch) -> None:
    seen: dict[str, object] = {}
    sentinel = object()
    monkeypatch.setattr(
        runtime, "create_app",
        lambda settings, **values: seen.update(values) or sentinel,
    )
    assert runtime.build_app(PlatformSettings(_secrets_dir=None)) is sentinel
    assert seen == {"research_resolver": None}


def test_factory_explicit_database_ownership_is_atomic() -> None:
    from liquent_platform.transport.http.app import create_app

    with pytest.raises(ValueError, match="owned database engine requires"):
        create_app(
            PlatformSettings(_secrets_dir=None), database_engine_owned=True
        )


def test_deployment_still_has_no_supervisor_socket_or_control_mount() -> None:
    compose = (
        Path(__file__).parents[1] / "operations/compose/compose.yaml"
    ).read_text(encoding="utf-8")
    control_plane = compose.split("  control-plane:", 1)[1].split(
        "  research-worker:", 1
    )[0]
    assert "docker.sock" not in control_plane
    assert "supervisor-control" not in control_plane
