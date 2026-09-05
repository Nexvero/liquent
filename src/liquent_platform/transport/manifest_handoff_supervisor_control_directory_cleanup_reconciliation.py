"""Read-only local reconciliation of claimed supervisor control directories."""

from collections.abc import Callable
from datetime import datetime, timezone
import os
from pathlib import Path

from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
    canonical_manifest_handoff_supervisor_control_artifact_name,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_directory_physical_cleanup import (
    SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup,
    _OPEN_DIRECTORY,
)


class SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation:
    """Classify one claimed leaf without changing any filesystem fact."""

    __slots__ = ("_attempts", "_claims", "_reader", "_clock")

    def __init__(
        self,
        root: Path,
        *,
        attempt_lookup: Callable,
        claim_lookup: Callable,
        directory_lookup: Callable,
        artifact_lookup: Callable,
        codec: CanonicalManifestHandoffSupervisorControlArtifactCodec,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            not callable(attempt_lookup)
            or not callable(claim_lookup)
            or (clock is not None and not callable(clock))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._attempts = attempt_lookup
        self._claims = claim_lookup
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._reader = SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup(
            root,
            claim_lookup=claim_lookup,
            directory_lookup=directory_lookup,
            artifact_lookup=artifact_lookup,
            codec=codec,
            clock=self._clock,
        )

    def __repr__(self) -> str:
        return "SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation()"

    def inspect_control_directory_cleanup(self, request):
        if type(request) is not ReconcileManifestHandoffSupervisorControlDirectoryCleanup:
            raise ManifestHandoffRegistryUnavailable
        root = leaf = None
        try:
            attempt = self._attempts(request.attempt_id)
            if attempt is None:
                return None
            if type(attempt) not in (
                ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
                ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if (
                attempt.attempt_id != request.attempt_id
                or attempt.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            claimed = self._claims(request.attempt_id)
            if (
                type(claimed) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup
                or claimed.attempt_id != request.attempt_id
                or claimed.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            current, retired, artifacts = self._reader._current(claimed)
            if current != claimed:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            root = self._reader._open_root()
            leaf_name = retired.leaf.value
            try:
                leaf = os.open(leaf_name, _OPEN_DIRECTORY, dir_fd=root)
            except FileNotFoundError:
                if not self._reader._same_root(root):
                    raise ManifestHandoffRegistryUnavailable
                outcome = ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome.ABSENT
            except OSError:
                outcome = ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome.CONFLICT
            else:
                expected = {
                    canonical_manifest_handoff_supervisor_control_artifact_name(role): record
                    for role, record in artifacts.items()
                }
                if self._reader._inventory(root, leaf_name, leaf, expected):
                    outcome = ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome.PRESENT
                else:
                    outcome = ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome.CONFLICT
            if self._attempts(request.attempt_id) != attempt:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            current_claim, current_retired, current_artifacts = self._reader._current(claimed)
            if (
                current_claim != claimed
                or current_retired != retired
                or current_artifacts != artifacts
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            inspected_at = self._now(claimed.claimed_at)
            return InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation(
                request, outcome, inspected_at
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if leaf is not None:
                self._reader._close(leaf)
            if root is not None:
                self._reader._close(root)

    def _now(self, lower):
        now = self._clock()
        if (
            type(now) is not datetime
            or now.tzinfo is None
            or now.utcoffset() != timezone.utc.utcoffset(now)
            or now < lower
        ):
            raise ManifestHandoffRegistryUnavailable
        return now
