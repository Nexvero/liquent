"""Profile-safe facade over persistent supervisor orchestration slices."""

from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorJournalState,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService,
    ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffWriterServiceResult,
    PrepareManifestHandoffRecoveryService,
    PrepareManifestHandoffWriterService,
    ReleaseManifestHandoffSupervisorService,
    TerminateManifestHandoffSupervisorService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class PersistentManifestHandoffSupervisorService:
    """Expose the existing writer and recovery service protocols as one facade."""

    __slots__ = ("_prepare", "_release", "_inspect", "_terminate", "_terminal")

    def __init__(self, *, prepare, release, inspect, terminate, terminal) -> None:
        dependencies = (prepare, release, inspect, terminate, terminal)
        if any(dependency is None for dependency in dependencies):
            raise ManifestHandoffRegistryUnavailable
        self._prepare, self._release, self._inspect, self._terminate, self._terminal = dependencies

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorService()"

    def prepare_writer(self, command):
        if type(command) is not PrepareManifestHandoffWriterService:
            raise ManifestHandoffRegistryUnavailable
        return self._call(self._prepare.prepare_writer, command,
            ManifestHandoffWriterServiceResult)

    def release_writer(self, command):
        if type(command) is not ReleaseManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        result = self._call(self._release.release_writer, command,
            ManifestHandoffWriterServiceResult)
        return self._complete(result, command, self._terminal.complete_writer,
            ManifestHandoffWriterServiceResult)

    def terminate_writer(self, command):
        if type(command) is not TerminateManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._call(self._terminate.terminate_writer, command,
            ManifestHandoffWriterServiceResult)

    def inspect_writer(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._inspect_call(self._inspect.inspect_writer, command,
            ManifestHandoffWriterServiceResult)

    def prepare_recovery(self, command):
        if type(command) is not PrepareManifestHandoffRecoveryService:
            raise ManifestHandoffRegistryUnavailable
        return self._call(self._prepare.prepare_recovery, command,
            ManifestHandoffRecoveryServiceResult)

    def release_recovery(self, command):
        if type(command) is not ReleaseManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        result = self._call(self._release.release_recovery, command,
            ManifestHandoffRecoveryServiceResult)
        return self._complete(result, command, self._terminal.complete_recovery,
            ManifestHandoffRecoveryServiceResult)

    def terminate_recovery(self, command):
        if type(command) is not TerminateManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._call(self._terminate.terminate_recovery, command,
            ManifestHandoffRecoveryServiceResult)

    def inspect_recovery(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._inspect_call(self._inspect.inspect_recovery, command,
            ManifestHandoffRecoveryServiceResult)

    def _complete(self, result, command, completion, result_type):
        if result is None or type(result) is ManifestHandoffSupervisorServiceConflict:
            return result
        if (type(result) is not result_type
                or result.journal.state is not ManifestHandoffSupervisorJournalState.RUNNING):
            raise ManifestHandoffRegistryUnavailable
        return self._call(completion,
            InspectManifestHandoffSupervisorService(command.handle_id), result_type)

    @staticmethod
    def _call(operation, command, result_type):
        try:
            result = operation(command)
            if result is None or type(result) in (result_type,
                    ManifestHandoffSupervisorServiceConflict):
                return result
            raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _inspect_call(operation, command, result_type):
        try:
            result = operation(command)
            if result is None or type(result) is result_type:
                return result
            raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
