from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)


def values():
    return {
        "proxy_socket": "/run/liquent/engine.sock",
        "daemon_socket": "/var/run/docker.sock",
        "control_root": "/srv/liquent/control",
        "source_root": "/srv/liquent/source",
        "target_root": "/srv/liquent/target",
        "writer_command": "/opt/liquent/writer-wrapper",
        "recovery_command": "/opt/liquent/recovery-wrapper",
        "proxy_uid": "10001", "client_gid": "10002",
        "daemon_uid": "0", "daemon_gid": "998",
        "host_owner_uid": "10001", "host_owner_gid": "10003",
        "data_owner_uid": "10004", "data_gid": "10005",
        "wrapper_uid": "10006", "wrapper_gid": "10007",
        "client_timeout_seconds": "15", "daemon_timeout_seconds": "30",
        "listener_backlog": "16", "maximum_exchanges": "10000",
    }


def test_complete_exact_mapping_builds_one_immutable_settings_value() -> None:
    result = ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(values())
    assert result.proxy_socket == Path("/run/liquent/engine.sock")
    assert result.daemon_uid == 0
    assert result.client_timeout_seconds == 15
    assert result.maximum_exchanges == 10_000
    with pytest.raises(FrozenInstanceError):
        result.proxy_uid = 1


@pytest.mark.parametrize("key", tuple(values()))
def test_every_missing_key_rejects_the_atomic_group(key) -> None:
    current = values()
    current.pop(key)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(current)


def test_extra_key_or_non_string_key_and_value_fail_closed() -> None:
    for mutation in (
        lambda current: current.update(extra="value"),
        lambda current: current.update(proxy_uid=10001),
        lambda current: current.update({1: "value"}),
    ):
        current = values()
        mutation(current)
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(current)


@pytest.mark.parametrize("key,value", (
    ("proxy_socket", "relative.sock"),
    ("proxy_socket", "/"),
    ("proxy_socket", "/run/../engine.sock"),
    ("proxy_socket", "/run//engine.sock"),
    ("target_root", "/srv/liquent/source"),
    ("writer_command", "writer-wrapper"),
    ("writer_command", "/opt/liquent/recovery-wrapper"),
    ("recovery_command", "/opt/liquent/recovery-wrapper/"),
))
def test_path_alias_overlap_or_nonabsolute_command_fails_closed(key, value) -> None:
    current = values()
    current[key] = value
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(current)


@pytest.mark.parametrize("key,value", (
    ("proxy_uid", "0"),
    ("daemon_uid", "-1"),
    ("client_gid", "010002"),
    ("wrapper_gid", "+10007"),
    ("data_gid", "true"),
    ("client_timeout_seconds", "301"),
    ("daemon_timeout_seconds", "0"),
    ("listener_backlog", "129"),
    ("maximum_exchanges", "1000001"),
    ("maximum_exchanges", "1.0"),
))
def test_identity_timeout_or_limit_outside_closed_range_fails_closed(key, value) -> None:
    current = values()
    current[key] = value
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(current)


def test_mapping_is_copied_without_retaining_caller_mutability() -> None:
    current = values()
    result = ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(current)
    current["proxy_uid"] = "99999"
    assert result.proxy_uid == 10001


def test_repr_contains_no_mapping_or_parser_dependency() -> None:
    result = ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(values())
    assert "from_mapping" not in repr(result)
    surface = vars(ManifestHandoffSupervisorEngineApiProxySettings)
    for name in ("from_env", "environment", "load", "reload", "allow"):
        assert name not in surface
