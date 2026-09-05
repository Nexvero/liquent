"""Compose one durable authoritative cleanup-retention operation."""

from collections.abc import Callable

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    BindManifestHandoffSupervisorControlDirectoryRetentionDecision,
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionOperationConflict,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorCleanupRetentionOperation:
    __slots__ = ("_directories", "_evaluation", "_operations", "_decision")

    def __init__(self, directories, evaluation, operations, *,
                 decision_id_generator: Callable[[], ManifestHandoffSupervisorControlDirectoryRetentionDecisionId]):
        if not all((callable(getattr(directories, "resolve_control_directory", None)),
                    callable(getattr(evaluation, "evaluate_control_directory_retention", None)),
                    callable(getattr(operations, "resolve_control_directory_retention_operation", None)),
                    callable(getattr(operations, "bind_control_directory_retention_decision", None)),
                    callable(decision_id_generator))):
            raise ManifestHandoffRegistryUnavailable
        self._directories = directories
        self._evaluation = evaluation
        self._operations = operations
        self._decision = decision_id_generator

    def execute(self, request):
        if type(request) is not EvaluateManifestHandoffSupervisorControlDirectoryRetention:
            raise ManifestHandoffRegistryUnavailable
        existing = self._operations.resolve_control_directory_retention_operation(
            request.operation_id
        )
        if existing is not None:
            return (existing if existing.evaluation.request.directory_id == request.directory_id
                    else ManifestHandoffSupervisorCleanupRetentionOperationConflict())
        lifecycle = self._directories.resolve_control_directory(request.directory_id)
        if type(lifecycle) is not RetiredManifestHandoffSupervisorControlDirectory:
            return None
        evaluation = self._evaluation.evaluate_control_directory_retention(request, lifecycle)
        if evaluation is None:
            return None
        decision_id = self._decision()
        if type(decision_id) is not ManifestHandoffSupervisorControlDirectoryRetentionDecisionId:
            raise ManifestHandoffRegistryUnavailable
        return self._operations.bind_control_directory_retention_decision(
            BindManifestHandoffSupervisorControlDirectoryRetentionDecision(
                evaluation, decision_id
            )
        )
