"""Closed private socket and kernel-peer authority for local proxy health."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthSocketAuthority:
    socket_path: Path
    socket_uid: int
    socket_gid: int
    parent_uid: int
    parent_gid: int
    peer_uid: int
    peer_gid: int
    timeout_seconds: int
    backlog: int

    @classmethod
    def from_mapping(
        cls, values: dict[str, str]
    ) -> "ManifestHandoffSupervisorEngineApiHealthSocketAuthority":
        names = {
            "socket_path", "socket_uid", "socket_gid", "parent_uid",
            "parent_gid", "peer_uid", "peer_gid", "timeout_seconds",
            "backlog",
        }
        try:
            if (
                type(values) is not dict
                or set(values) != names
                or any(type(key) is not str or type(value) is not str
                       for key, value in values.items())
            ):
                raise ManifestHandoffRegistryUnavailable
            raw_path = values["socket_path"]
            path = Path(raw_path)
            if str(path) != raw_path:
                raise ManifestHandoffRegistryUnavailable
            integers = {
                name: _integer(values[name]) for name in names - {"socket_path"}
            }
            return cls(socket_path=path, **integers)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __post_init__(self) -> None:
        path = self.socket_path
        integers = (
            self.socket_uid, self.socket_gid, self.parent_uid, self.parent_gid,
            self.peer_uid, self.peer_gid, self.timeout_seconds, self.backlog,
        )
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or path.parent == Path("/")
            or ".." in path.parts
            or str(path) != str(self.socket_path)
            or any(type(value) is not int for value in integers)
            or any(value < 1 or value > 2_147_483_647 for value in integers[:6])
            or self.timeout_seconds < 1
            or self.timeout_seconds > 300
            or self.backlog < 1
            or self.backlog > 128
        ):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthSocketAuthority()"

    def client_peer_policy(
        self,
    ) -> LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy:
        try:
            return LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
                local_socket=self.socket_path,
                client_uid=self.peer_uid,
                client_gid=self.peer_gid,
                timeout_seconds=self.timeout_seconds,
            )
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


def _integer(value: str) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdigit()
        or (len(value) > 1 and value.startswith("0"))
    ):
        raise ManifestHandoffRegistryUnavailable
    parsed = int(value)
    if parsed > 2_147_483_647:
        raise ManifestHandoffRegistryUnavailable
    return parsed
