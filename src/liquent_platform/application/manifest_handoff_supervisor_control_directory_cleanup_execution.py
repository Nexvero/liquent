"""Controlled one-shot supervisor control-directory cleanup composition."""

from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    CompletedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupOutcome,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight,
    ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup,
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    PreflightManifestHandoffSupervisorControlDirectoryCleanup,
    PreparedManifestHandoffSupervisorControlDirectoryCleanup,
    RemovedManifestHandoffSupervisorControlDirectory,
    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorControlDirectoryCleanupExecution:
    """Preflight, claim, execute once, and durably classify one cleanup."""

    __slots__ = ("_attempts", "_preflight", "_claims", "_physical", "_outcomes")

    def __init__(self, *, attempts, preflight, claims, physical, outcomes) -> None:
        if not all((
            callable(getattr(attempts, "resolve_cleanup_attempt", None)),
            callable(getattr(attempts, "complete_cleanup_attempt", None)),
            callable(getattr(preflight, "prepare_control_directory_cleanup", None)),
            callable(getattr(claims, "claim_control_directory_cleanup_write", None)),
            callable(getattr(physical, "remove_control_directory", None)),
            callable(getattr(outcomes, "persist_control_directory_cleanup_physical_outcome", None)),
        )):
            raise ManifestHandoffRegistryUnavailable
        self._attempts = attempts
        self._preflight = preflight
        self._claims = claims
        self._physical = physical
        self._outcomes = outcomes

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorControlDirectoryCleanupExecution()"

    def cleanup_control_directory(self, request):
        if type(request) is not CleanupManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        try:
            current = self._attempts.resolve_cleanup_attempt(request.attempt_id)
            if current is None:
                return None
            if type(current) is not CleanupManifestHandoffSupervisorControlDirectory:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if current != request:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            preflight = self._preflight.prepare_control_directory_cleanup(
                PreflightManifestHandoffSupervisorControlDirectoryCleanup(
                    request.attempt_id, request.directory_id
                )
            )
            if type(preflight) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
                return preflight
            if preflight is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if type(preflight) is AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight:
                return self._complete_absent(request, preflight)
            if type(preflight) is not PreparedManifestHandoffSupervisorControlDirectoryCleanup:
                raise ManifestHandoffRegistryUnavailable
            if (
                preflight.attempt_id != request.attempt_id
                or preflight.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            claimed = self._claims.claim_control_directory_cleanup_write(
                ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup(preflight)
            )
            if type(claimed) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
                return claimed
            if claimed is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if (
                type(claimed) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup
                or claimed.prepared != preflight
            ):
                raise ManifestHandoffRegistryUnavailable
            physical = self._execute_once_or_unknown(claimed)
            persisted = self._outcomes.persist_control_directory_cleanup_physical_outcome(
                physical
            )
            return self._validated_persisted(physical, persisted)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _complete_absent(self, request, preflight):
        if (
            preflight.attempt_id != request.attempt_id
            or preflight.directory_id != request.directory_id
        ):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        completed = self._attempts.complete_cleanup_attempt(
            request.attempt_id,
            request.directory_id,
            ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT,
        )
        if type(completed) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
            return completed
        if completed is None:
            raise ManifestHandoffRegistryUnavailable
        if (
            type(completed) is not CompletedManifestHandoffSupervisorControlDirectoryCleanup
            or completed.attempt_id != request.attempt_id
            or completed.directory_id != request.directory_id
            or completed.outcome is not ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT
        ):
            raise ManifestHandoffRegistryUnavailable
        return completed

    def _execute_once_or_unknown(self, claimed):
        try:
            physical = self._physical.remove_control_directory(claimed)
        except Exception:
            return self._unknown(claimed)
        if type(physical) is RemovedManifestHandoffSupervisorControlDirectory:
            if not self._same_claim(physical, claimed):
                return self._unknown(claimed)
            return physical
        if type(physical) is UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect:
            if self._same_claim(physical, claimed):
                return physical
        return self._unknown(claimed)

    @staticmethod
    def _same_claim(outcome, claimed):
        return all((
            outcome.claim_id == claimed.claim_id,
            outcome.attempt_id == claimed.attempt_id,
            outcome.directory_id == claimed.directory_id,
        ))

    @staticmethod
    def _unknown(claimed):
        return UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect(
            claimed.claim_id, claimed.attempt_id, claimed.directory_id
        )

    @staticmethod
    def _validated_persisted(physical, persisted):
        if type(physical) is RemovedManifestHandoffSupervisorControlDirectory:
            if (
                type(persisted) is CompletedManifestHandoffSupervisorControlDirectoryCleanup
                and persisted.attempt_id == physical.attempt_id
                and persisted.directory_id == physical.directory_id
                and persisted.outcome is ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED
                and persisted.completed_at == physical.removed_at
            ):
                return persisted
        elif type(physical) is UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect:
            if (
                type(persisted) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired
                and persisted.attempt_id == physical.attempt_id
                and persisted.directory_id == physical.directory_id
            ):
                return persisted
        raise ManifestHandoffRegistryUnavailable
