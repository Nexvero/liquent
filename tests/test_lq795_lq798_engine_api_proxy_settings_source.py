import os
from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings_source import (
    load_manifest_handoff_supervisor_engine_api_proxy_settings,
)


VALUES = {
    "PROXY_SOCKET": "/run/liquent/engine.sock",
    "DAEMON_SOCKET": "/var/run/docker.sock",
    "CONTROL_ROOT": "/srv/liquent/control",
    "SOURCE_ROOT": "/srv/liquent/source",
    "TARGET_ROOT": "/srv/liquent/target",
    "WRITER_COMMAND": "/opt/liquent/writer-wrapper",
    "RECOVERY_COMMAND": "/opt/liquent/recovery-wrapper",
    "PROXY_UID": "10001", "CLIENT_GID": "10002",
    "DAEMON_UID": "0", "DAEMON_GID": "998",
    "HOST_OWNER_UID": "10003", "HOST_OWNER_GID": "10004",
    "DATA_OWNER_UID": "10005", "DATA_GID": "10006",
    "WRAPPER_UID": "10007", "WRAPPER_GID": "10008",
    "CLIENT_TIMEOUT_SECONDS": "15", "DAEMON_TIMEOUT_SECONDS": "30",
    "LISTENER_BACKLOG": "16", "MAXIMUM_EXCHANGES": "10000",
}


def _file(path: Path, values=VALUES) -> Path:
    path.write_text("".join(
        f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_{key}={value}\n"
        for key, value in values.items()
    ), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_owner_private_exact_projection_loads_closed_settings(tmp_path: Path) -> None:
    result = load_manifest_handoff_supervisor_engine_api_proxy_settings(
        _file(tmp_path / "proxy.env")
    )
    assert type(result) is ManifestHandoffSupervisorEngineApiProxySettings
    assert result.proxy_socket == Path("/run/liquent/engine.sock")
    assert result.host_owner_uid == 10003
    assert result.maximum_exchanges == 10_000


@pytest.mark.parametrize("mode", (0o400, 0o640, 0o644, 0o660))
def test_nonexact_owner_only_mode_fails_closed(tmp_path: Path, mode: int) -> None:
    path = _file(tmp_path / "proxy.env")
    path.chmod(mode)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_proxy_settings(path)


def test_symlink_hardlink_directory_and_relative_path_fail_closed(tmp_path: Path) -> None:
    source = _file(tmp_path / "source.env")
    symlink = tmp_path / "symlink.env"
    symlink.symlink_to(source)
    hardlink = tmp_path / "hardlink.env"
    os.link(source, hardlink)
    for path in (symlink, source, hardlink, tmp_path, Path("relative.env")):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            load_manifest_handoff_supervisor_engine_api_proxy_settings(path)


@pytest.mark.parametrize("mutation", (
    lambda lines: lines[:-1],
    lambda lines: lines + ["EXTRA=value\n"],
    lambda lines: lines + [lines[0]],
    lambda lines: ["# comment\n", *lines],
    lambda lines: [lines[0].replace("=", " =", 1), *lines[1:]],
    lambda lines: [lines[0].rstrip("\n"), *lines[1:]],
    lambda lines: [lines[0].replace("=", "==", 1), *lines[1:]],
))
def test_missing_extra_duplicate_or_noncanonical_line_fails_closed(
    tmp_path: Path, mutation
) -> None:
    canonical = [
        f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_{key}={value}\n"
        for key, value in VALUES.items()
    ]
    path = tmp_path / "proxy.env"
    path.write_text("".join(mutation(canonical)), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_proxy_settings(path)


def test_invalid_utf8_empty_and_oversized_files_fail_closed(tmp_path: Path) -> None:
    for number, content in enumerate((b"", b"\xff\n", b"x" * 16_385)):
        path = tmp_path / f"proxy-{number}.env"
        path.write_bytes(content)
        path.chmod(0o600)
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            load_manifest_handoff_supervisor_engine_api_proxy_settings(path)


def test_invalid_projected_value_is_rejected_by_closed_settings_parser(
    tmp_path: Path,
) -> None:
    values = dict(VALUES, PROXY_UID="0")
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_proxy_settings(
            _file(tmp_path / "proxy.env", values)
        )


def test_loader_does_not_read_process_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(
        "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_PROXY_UID", "99999"
    )
    result = load_manifest_handoff_supervisor_engine_api_proxy_settings(
        _file(tmp_path / "proxy.env")
    )
    assert result.proxy_uid == 10001
