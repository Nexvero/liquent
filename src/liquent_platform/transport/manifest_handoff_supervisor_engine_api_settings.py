"""Closed complete settings value for the private Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_PATHS = (
    "proxy_socket", "daemon_socket", "control_root", "source_root", "target_root",
)
_COMMANDS = ("writer_command", "recovery_command")
_POSITIVE_IDS = (
    "proxy_uid", "client_gid", "daemon_gid", "host_owner_uid",
    "host_owner_gid", "data_owner_uid", "data_gid", "wrapper_uid",
    "wrapper_gid",
)
_ALL = frozenset(
    _PATHS + _COMMANDS + _POSITIVE_IDS + (
        "daemon_uid", "client_timeout_seconds", "daemon_timeout_seconds",
        "listener_backlog", "maximum_exchanges",
    )
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiProxySettings:
    proxy_socket: Path
    daemon_socket: Path
    control_root: Path
    source_root: Path
    target_root: Path
    writer_command: str
    recovery_command: str
    proxy_uid: int
    client_gid: int
    daemon_uid: int
    daemon_gid: int
    host_owner_uid: int
    host_owner_gid: int
    data_owner_uid: int
    data_gid: int
    wrapper_uid: int
    wrapper_gid: int
    client_timeout_seconds: int
    daemon_timeout_seconds: int
    listener_backlog: int
    maximum_exchanges: int

    @classmethod
    def from_mapping(
        cls, values: dict[str, str]
    ) -> "ManifestHandoffSupervisorEngineApiProxySettings":
        try:
            if (
                type(values) is not dict
                or set(values) != _ALL
                or any(type(key) is not str or type(value) is not str
                       for key, value in values.items())
            ):
                raise ManifestHandoffRegistryUnavailable
            paths = {name: _path(values[name]) for name in _PATHS}
            if len(set(paths.values())) != len(paths):
                raise ManifestHandoffRegistryUnavailable
            commands = {name: _command(values[name]) for name in _COMMANDS}
            if len(set(commands.values())) != len(commands):
                raise ManifestHandoffRegistryUnavailable
            integers = {
                name: _integer(values[name], minimum=1, maximum=2_147_483_647)
                for name in _POSITIVE_IDS
            }
            integers["daemon_uid"] = _integer(
                values["daemon_uid"], minimum=0, maximum=2_147_483_647
            )
            integers["client_timeout_seconds"] = _integer(
                values["client_timeout_seconds"], minimum=1, maximum=300
            )
            integers["daemon_timeout_seconds"] = _integer(
                values["daemon_timeout_seconds"], minimum=1, maximum=300
            )
            integers["listener_backlog"] = _integer(
                values["listener_backlog"], minimum=1, maximum=128
            )
            integers["maximum_exchanges"] = _integer(
                values["maximum_exchanges"], minimum=1, maximum=1_000_000
            )
            return cls(**paths, **commands, **integers)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


def _path(value: str) -> Path:
    path = Path(value)
    if (
        not value
        or not path.is_absolute()
        or path == Path("/")
        or ".." in path.parts
        or str(path) != value
    ):
        raise ManifestHandoffRegistryUnavailable
    return path


def _command(value: str) -> str:
    path = _path(value)
    if value.endswith("/") or path.name in ("", "."):
        raise ManifestHandoffRegistryUnavailable
    return value


def _integer(value: str, *, minimum: int, maximum: int) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdigit()
        or (len(value) > 1 and value.startswith("0"))
    ):
        raise ManifestHandoffRegistryUnavailable
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ManifestHandoffRegistryUnavailable
    return parsed
