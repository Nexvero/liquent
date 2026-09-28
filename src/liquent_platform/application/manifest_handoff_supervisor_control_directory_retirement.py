"""Controlled retirement of terminal supervisor control directories."""

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ActiveManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryConflict,
    ReservedManifestHandoffSupervisorControlDirectory,
    RetireManifestHandoffSupervisorControlDirectory,
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


class PersistentManifestHandoffSupervisorControlDirectoryRetirement:
    """Retire one active binding only after its durable terminal journal fact."""

    __slots__ = ("_registry", "_journal")

    def __init__(self, *, registry, journal) -> None:
        if registry is None or journal is None:
            raise ManifestHandoffRegistryUnavailable
        self._registry = registry
        self._journal = journal

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorControlDirectoryRetirement()"

    def retire(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> RetiredManifestHandoffSupervisorControlDirectory | ManifestHandoffSupervisorControlDirectoryConflict | None:
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        try:
            lifecycle = self._registry.resolve_control_directory(directory_id)
            if lifecycle is None:
                return None
            if type(lifecycle) is RetiredManifestHandoffSupervisorControlDirectory:
                return lifecycle
            if type(lifecycle) is ReservedManifestHandoffSupervisorControlDirectory:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if type(lifecycle) is not ActiveManifestHandoffSupervisorControlDirectory:
                raise ManifestHandoffRegistryUnavailable

            writer = self._journal.inspect_writer_journal(lifecycle.handle_id)
            recovery = self._journal.inspect_recovery_journal(lifecycle.handle_id)
            views = [view for view in (writer, recovery) if view is not None]
            if len(views) != 1:
                raise ManifestHandoffRegistryUnavailable
            terminal = views[0]
            if type(terminal) not in (
                ManifestHandoffWriterJournalView,
                ManifestHandoffRecoveryJournalView,
            ):
                raise ManifestHandoffRegistryUnavailable
            if terminal.registration.handle_id != lifecycle.handle_id:
                raise ManifestHandoffRegistryUnavailable
            if terminal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if (
                terminal.terminal_observation_id is None
                or terminal.result is None
                or terminal.result.handle_id != lifecycle.handle_id
            ):
                raise ManifestHandoffRegistryUnavailable

            retired = self._registry.retire_control_directory(
                RetireManifestHandoffSupervisorControlDirectory(lifecycle)
            )
            if type(retired) is ManifestHandoffSupervisorControlDirectoryConflict:
                return retired
            if retired is None or type(retired) is not RetiredManifestHandoffSupervisorControlDirectory:
                raise ManifestHandoffRegistryUnavailable
            if retired.active != lifecycle:
                raise ManifestHandoffRegistryUnavailable
            return retired
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
