from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition as composition
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessPhase,
    ManifestHandoffSupervisorEngineApiProcessStatus,
    ManifestHandoffSupervisorEngineApiReadinessProbe,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import (
    SignalOwnedManifestHandoffSupervisorEngineApiRun,
)


def settings():
    return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
        "proxy_socket": "/run/liquent/engine.sock", "daemon_socket": "/var/run/docker.sock",
        "control_root": "/srv/liquent/control", "source_root": "/srv/liquent/source",
        "target_root": "/srv/liquent/target", "writer_command": "/opt/liquent/writer",
        "recovery_command": "/opt/liquent/recovery", "proxy_uid": "10001",
        "client_gid": "10002", "daemon_uid": "0", "daemon_gid": "998",
        "host_owner_uid": "10003", "host_owner_gid": "10004",
        "data_owner_uid": "10005", "data_gid": "10006", "wrapper_uid": "10007",
        "wrapper_gid": "10008", "client_timeout_seconds": "15",
        "daemon_timeout_seconds": "30", "listener_backlog": "16",
        "maximum_exchanges": "10000",
    })


def test_bundle_exposes_one_identity_bound_run_status_and_probe() -> None:
    bundle = composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings()
    )
    assert type(bundle) is composition.ManifestHandoffSupervisorEngineApiProcessBundle
    assert type(bundle.process_run) is SignalOwnedManifestHandoffSupervisorEngineApiRun
    assert type(bundle.status) is ManifestHandoffSupervisorEngineApiProcessStatus
    assert type(bundle.readiness) is ManifestHandoffSupervisorEngineApiReadinessProbe
    assert bundle.process_run._process._status is bundle.status
    assert bundle.readiness._status is bundle.status
    assert bundle.status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL
    assert bundle.readiness.check().ready is False


def test_compatibility_composer_projects_only_the_same_bundle_run(monkeypatch) -> None:
    sentinel = object()

    class Bundle:
        process_run = sentinel

    seen = []
    monkeypatch.setattr(
        composition, "compose_manifest_handoff_supervisor_engine_api_proxy_bundle",
        lambda value: seen.append(value) or Bundle(),
    )
    current = settings()
    assert composition.compose_manifest_handoff_supervisor_engine_api_proxy(current) is sentinel
    assert seen == [current]


def test_bundle_is_frozen_and_repr_is_detail_free() -> None:
    bundle = composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings()
    )
    with pytest.raises(FrozenInstanceError):
        bundle.status = ManifestHandoffSupervisorEngineApiProcessStatus()
    assert repr(bundle) == "ManifestHandoffSupervisorEngineApiProcessBundle()"
    assert "engine.sock" not in repr(bundle)


def test_bundle_rejects_mismatched_or_foreign_components() -> None:
    first = composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings()
    )
    second = composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings()
    )
    for values in (
        (object(), first.status, first.readiness),
        (first.process_run, object(), first.readiness),
        (first.process_run, first.status, object()),
        (first.process_run, second.status, first.readiness),
        (first.process_run, first.status, second.readiness),
    ):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            composition.ManifestHandoffSupervisorEngineApiProcessBundle(*values)


def test_bundle_composition_performs_no_host_environment_or_run_effect(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("effect during bundle composition")

    for name in ("open", "lstat", "getenv", "run"):
        monkeypatch.setattr(composition, name, forbidden, raising=False)
    bundle = composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings()
    )
    assert bundle.status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL


@pytest.mark.parametrize("value", (None, object(), {}, Path("/settings")))
def test_bundle_composition_accepts_only_exact_settings(value) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition.compose_manifest_handoff_supervisor_engine_api_proxy_bundle(value)
