"""Controlled read-only reconciliation of uncertain supervisor cleanup."""

from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
    ReconciledManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation,
    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorControlDirectoryCleanupReconciliation:
    """Secure a crashed claim, inspect once read-only, and persist classification."""

    __slots__ = ("_attempts", "_outcomes", "_physical")

    def __init__(self, *, attempts, outcomes, physical) -> None:
        if not all((
            callable(getattr(attempts, "resolve_cleanup_attempt", None)),
            callable(getattr(attempts, "record_cleanup_reconciliation", None)),
            callable(getattr(outcomes, "persist_control_directory_cleanup_physical_outcome", None)),
            callable(getattr(physical, "inspect_control_directory_cleanup", None)),
        )):
            raise ManifestHandoffRegistryUnavailable
        self._attempts = attempts
        self._outcomes = outcomes
        self._physical = physical

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorControlDirectoryCleanupReconciliation()"

    def reconcile_control_directory_cleanup(self, request):
        if type(request) is not ReconcileManifestHandoffSupervisorControlDirectoryCleanup:
            raise ManifestHandoffRegistryUnavailable
        try:
            current = self._attempts.resolve_cleanup_attempt(request.attempt_id)
            if current is None:
                return None
            if type(current) is ClaimedManifestHandoffSupervisorControlDirectoryCleanup:
                if (
                    current.attempt_id != request.attempt_id
                    or current.directory_id != request.directory_id
                ):
                    return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
                secured = self._outcomes.persist_control_directory_cleanup_physical_outcome(
                    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect(
                        current.claim_id, current.attempt_id, current.directory_id
                    )
                )
                if (
                    type(secured) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired
                    or secured.attempt_id != request.attempt_id
                    or secured.directory_id != request.directory_id
                ):
                    raise ManifestHandoffRegistryUnavailable
                current = secured
            if type(current) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if (
                current.attempt_id != request.attempt_id
                or current.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            inspected = self._physical.inspect_control_directory_cleanup(request)
            if type(inspected) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
                return inspected
            if inspected is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if (
                type(inspected) is not InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation
                or inspected.request != request
            ):
                raise ManifestHandoffRegistryUnavailable
            reconciled = self._attempts.record_cleanup_reconciliation(
                request, inspected.outcome
            )
            if type(reconciled) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
                return reconciled
            if reconciled is None:
                raise ManifestHandoffRegistryUnavailable
            if (
                type(reconciled) is not ReconciledManifestHandoffSupervisorControlDirectoryCleanup
                or reconciled.attempt_id != request.attempt_id
                or reconciled.directory_id != request.directory_id
                or reconciled.outcome is not inspected.outcome
            ):
                raise ManifestHandoffRegistryUnavailable
            return reconciled
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
