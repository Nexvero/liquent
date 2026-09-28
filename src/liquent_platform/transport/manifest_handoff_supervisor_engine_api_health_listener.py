"""Controlled private Unix listener lifecycle for Engine API health."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import (
    ControlledManifestHandoffSupervisorEngineApiListener,
)


class ControlledManifestHandoffSupervisorEngineApiHealthListener:
    """Own one health listener while reusing the hardened socket lifecycle."""

    __slots__ = ("_lifecycle",)

    def __init__(self, *, socket_path: Path, socket_uid: int, client_gid: int,
                 parent_uid: int, parent_gid: int, backlog: int,
                 socket_factory: Callable[[int, int], object] | None = None) -> None:
        try:
            self._lifecycle = ControlledManifestHandoffSupervisorEngineApiListener(
                socket_path=socket_path, proxy_uid=socket_uid, client_gid=client_gid,
                parent_uid=parent_uid, parent_gid=parent_gid, backlog=backlog,
                socket_factory=socket_factory,
            )
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorEngineApiHealthListener()"

    def open(self):
        try:
            return self._lifecycle.open()
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def close(self, listener) -> None:
        try:
            self._lifecycle.close(listener)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
