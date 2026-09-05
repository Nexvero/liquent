import os
from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import (
    ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_settings_source import (
    load_manifest_handoff_supervisor_engine_api_health_authority,
)


VALUES = {
    "SOCKET_PATH": "/run/liquent/health.sock",
    "SOCKET_UID": "10001", "SOCKET_GID": "10002",
    "PARENT_UID": "10003", "PARENT_GID": "10004",
    "PEER_UID": "10005", "PEER_GID": "10006",
    "TIMEOUT_SECONDS": "5", "BACKLOG": "8",
}


def mapping(**changes):
    values = {key.lower(): value for key, value in VALUES.items()}
    values.update(changes)
    return values


def private_file(path: Path, values=VALUES):
    path.write_text("".join(
        f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_{key}={value}\n"
        for key, value in values.items()
    ), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_exact_mapping_builds_complete_health_authority() -> None:
    result = ManifestHandoffSupervisorEngineApiHealthSocketAuthority.from_mapping(
        mapping()
    )
    assert result.socket_path == Path("/run/liquent/health.sock")
    assert result.peer_uid == 10005
    assert result.timeout_seconds == 5


@pytest.mark.parametrize("key", tuple(mapping()))
def test_every_missing_mapping_key_fails_atomically(key) -> None:
    values = mapping()
    values.pop(key)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiHealthSocketAuthority.from_mapping(values)


@pytest.mark.parametrize("change", (
    {"extra": "value"}, {"socket_uid": "010001"}, {"peer_uid": "+10005"},
    {"timeout_seconds": "true"}, {"backlog": "1.0"},
    {"socket_path": "/run//liquent/health.sock"},
))
def test_extra_noncanonical_number_or_path_fails_closed(change) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiHealthSocketAuthority.from_mapping(
            mapping(**change)
        )


def test_owner_private_file_projects_exact_authority(tmp_path: Path) -> None:
    result = load_manifest_handoff_supervisor_engine_api_health_authority(
        private_file(tmp_path / "health.env")
    )
    assert result == ManifestHandoffSupervisorEngineApiHealthSocketAuthority.from_mapping(
        mapping()
    )


@pytest.mark.parametrize("mode", (0o400, 0o640, 0o644, 0o660))
def test_file_requires_exact_owner_only_mode(tmp_path: Path, mode) -> None:
    path = private_file(tmp_path / "health.env")
    path.chmod(mode)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_health_authority(path)


def test_symlink_and_hardlink_fail_closed(tmp_path: Path) -> None:
    source = private_file(tmp_path / "source.env")
    symlink = tmp_path / "symlink.env"
    symlink.symlink_to(source)
    hardlink = tmp_path / "hardlink.env"
    os.link(source, hardlink)
    for path in (source, symlink, hardlink):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            load_manifest_handoff_supervisor_engine_api_health_authority(path)


@pytest.mark.parametrize("mutation", (
    lambda lines: lines[:-1],
    lambda lines: lines + ["EXTRA=value\n"],
    lambda lines: lines + [lines[0]],
    lambda lines: ["# comment\n", *lines],
    lambda lines: [lines[0].replace("=", "==", 1), *lines[1:]],
))
def test_nonexact_file_projection_fails_closed(tmp_path: Path, mutation) -> None:
    lines = [
        f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_{key}={value}\n"
        for key, value in VALUES.items()
    ]
    path = tmp_path / "health.env"
    path.write_text("".join(mutation(lines)), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_health_authority(path)


def test_process_environment_cannot_override_private_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(
        "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_PEER_UID", "99999"
    )
    result = load_manifest_handoff_supervisor_engine_api_health_authority(
        private_file(tmp_path / "health.env")
    )
    assert result.peer_uid == 10005
