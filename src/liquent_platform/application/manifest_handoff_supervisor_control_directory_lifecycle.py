"""Retry-safe composition of persistent and physical control-directory facts."""

from pathlib import Path

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ActivateManifestHandoffSupervisorControlDirectory,
    ActiveManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryConflict,
    ReserveManifestHandoffSupervisorControlDirectory,
    ReservedManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


class PersistentManifestHandoffSupervisorControlDirectoryLifecycle:
    """Reserve, create, and activate one immutable directory binding."""

    __slots__ = ("_registry", "_directories")

    def __init__(self, *, registry, directories) -> None:
        if registry is None or directories is None:
            raise ManifestHandoffRegistryUnavailable
        self._registry = registry
        self._directories = directories

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorControlDirectoryLifecycle()"

    def ensure_active(
        self, request: ReserveManifestHandoffSupervisorControlDirectory
    ) -> (
        ActiveManifestHandoffSupervisorControlDirectory
        | ManifestHandoffSupervisorControlDirectoryConflict
        | None
    ):
        if type(request) is not ReserveManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        try:
            reservation = self._registry.reserve_control_directory(request)
            if reservation is None:
                return None
            if type(reservation) is ManifestHandoffSupervisorControlDirectoryConflict:
                return reservation
            if type(reservation) is not ReservedManifestHandoffSupervisorControlDirectory:
                raise ManifestHandoffRegistryUnavailable

            created = self._directories.create_reserved(reservation)
            if type(created) is ManifestHandoffSupervisorControlDirectoryConflict:
                return created
            if not isinstance(created, Path):
                raise ManifestHandoffRegistryUnavailable

            active = self._registry.activate_control_directory(
                ActivateManifestHandoffSupervisorControlDirectory(reservation)
            )
            if type(active) is ManifestHandoffSupervisorControlDirectoryConflict:
                return active
            if active is None or type(active) is not ActiveManifestHandoffSupervisorControlDirectory:
                raise ManifestHandoffRegistryUnavailable
            if active.reservation != reservation:
                raise ManifestHandoffRegistryUnavailable
            return active
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
