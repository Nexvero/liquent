"""Explicit opt-in composition for supervisor control-directory cleanup."""

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import secrets

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ControlledManifestHandoffSupervisorControlDirectoryCleanupExecution,
)
from liquent_platform.application.manifest_handoff_supervisor_control_directory_cleanup_reconciliation import (
    ControlledManifestHandoffSupervisorControlDirectoryCleanupReconciliation,
)
from liquent_platform.application.manifest_handoff_supervisor_cleanup_retention_evaluation import (
    AuthoritativeManifestHandoffSupervisorCleanupRetentionEvaluation,
)
from liquent_platform.application.manifest_handoff_supervisor_cleanup_retention_operation import (
    ControlledManifestHandoffSupervisorCleanupRetentionOperation,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention_policy import (
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_clearance_creation import (
    DatabaseManifestHandoffSupervisorCleanupClearanceCreation,
)
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_retention_operation import (
    DatabaseManifestHandoffSupervisorCleanupRetentionOperations,
)
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_retention_policy import (
    DatabaseManifestHandoffSupervisorCleanupRetentionPolicy,
)
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import (
    DatabaseManifestHandoffSupervisorControlDirectories,
)
from liquent_platform.persistence.manifest_handoff_supervisor_control_directory_cleanup import (
    DatabaseManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.persistence.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance,
)
from liquent_platform.persistence.manifest_handoff_supervisor_control_directory_cleanup_write_claim import (
    DatabaseManifestHandoffSupervisorControlDirectoryCleanupWriteClaims,
)
from liquent_platform.persistence.manifest_handoff_supervisor_journal import (
    DatabaseManifestHandoffSupervisorJournal,
)
from liquent_platform.persistence.manifest_handoff_supervisor_runtime import (
    DatabaseManifestHandoffSupervisorRuntime,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_directory_cleanup_preflight import (
    SafeLocalManifestHandoffSupervisorControlDirectoryCleanupPreflight,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_directory_cleanup_reconciliation import (
    SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation,
)
from liquent_platform.transport.manifest_handoff_supervisor_control_directory_physical_cleanup import (
    SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup,
)


class ManifestHandoffSupervisorControlDirectoryCleanupComposition:
    """Expose only the three controlled cleanup entry points."""

    __slots__ = ("retention_operation", "clearance_creation", "execution", "reconciliation")

    def __init__(self, *, retention_operation, clearance_creation, execution, reconciliation) -> None:
        self.retention_operation = retention_operation
        self.clearance_creation = clearance_creation
        self.execution = execution
        self.reconciliation = reconciliation


def compose_manifest_handoff_supervisor_cleanup_retention_operation(
    *, database_engine: Engine, clock: Callable[[], datetime] | None = None,
    directory_lookup=None,
):
    if not isinstance(database_engine, Engine) or (clock is not None and not callable(clock)):
        raise ManifestHandoffRegistryUnavailable
    directories = directory_lookup or DatabaseManifestHandoffSupervisorControlDirectories(
        database_engine, clock=clock
    )
    policies = DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(
        database_engine,
        clock=clock or (lambda: datetime.now(timezone.utc)),
        policy_revision_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(secrets.token_hex(32)),
        authority_revision_generator=lambda: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(secrets.token_hex(32)),
    )
    evaluation = AuthoritativeManifestHandoffSupervisorCleanupRetentionEvaluation(
        policies, clock=clock or (lambda: datetime.now(timezone.utc))
    )
    store = DatabaseManifestHandoffSupervisorCleanupRetentionOperations(
        database_engine, clock=clock
    )
    return ControlledManifestHandoffSupervisorCleanupRetentionOperation(
        directories, evaluation, store,
        decision_id_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionDecisionId(secrets.token_hex(32)),
    )


def compose_manifest_handoff_supervisor_control_directory_cleanup(
    *,
    database_engine: Engine,
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId,
    control_directory_root: Path,
    clock: Callable[[], datetime] | None = None,
) -> ManifestHandoffSupervisorControlDirectoryCleanupComposition:
    """Build one inert cleanup graph from explicitly controlled dependencies."""
    if (
        not isinstance(database_engine, Engine)
        or type(backend_instance_id) is not ManifestHandoffSupervisorBackendInstanceId
        or not isinstance(control_directory_root, Path)
        or not control_directory_root.is_absolute()
        or (clock is not None and not callable(clock))
    ):
        raise ManifestHandoffRegistryUnavailable
    try:
        directories = DatabaseManifestHandoffSupervisorControlDirectories(
            database_engine, clock=clock
        )
        attempts = DatabaseManifestHandoffSupervisorControlDirectoryCleanup(
            database_engine, clock=clock
        )
        retention_operation = compose_manifest_handoff_supervisor_cleanup_retention_operation(
            database_engine=database_engine, clock=clock, directory_lookup=directories,
        )
        runtime = DatabaseManifestHandoffSupervisorRuntime(database_engine, clock=clock)
        journal = DatabaseManifestHandoffSupervisorJournal(
            database_engine, backend_instance_id=backend_instance_id, clock=clock
        )
        clearances = DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance(
            database_engine,
            directory_lookup=directories,
            decision_lookup=attempts,
            writer_journal_lookup=journal.inspect_writer_journal,
            recovery_journal_lookup=journal.inspect_recovery_journal,
        )
        clearance_creation = DatabaseManifestHandoffSupervisorCleanupClearanceCreation(
            database_engine, clock=clock
        )
        claims = DatabaseManifestHandoffSupervisorControlDirectoryCleanupWriteClaims(
            database_engine, clock=clock
        )
        codec = CanonicalManifestHandoffSupervisorControlArtifactCodec()
        preflight = SafeLocalManifestHandoffSupervisorControlDirectoryCleanupPreflight(
            control_directory_root,
            attempt_lookup=attempts.resolve_cleanup_attempt,
            clearance_lookup=clearances.resolve_control_directory_cleanup_clearance,
            artifact_lookup=runtime.resolve_artifact_role,
            codec=codec,
            clock=clock,
        )
        physical = SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup(
            control_directory_root,
            claim_lookup=claims.resolve_control_directory_cleanup_write_claim,
            directory_lookup=directories.resolve_control_directory,
            artifact_lookup=runtime.resolve_artifact_role,
            codec=codec,
            clock=clock,
        )
        physical_reconciliation = (
            SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation(
                control_directory_root,
                attempt_lookup=attempts.resolve_cleanup_attempt,
                claim_lookup=claims.resolve_control_directory_cleanup_write_claim,
                directory_lookup=directories.resolve_control_directory,
                artifact_lookup=runtime.resolve_artifact_role,
                codec=codec,
                clock=clock,
            )
        )
        execution = ControlledManifestHandoffSupervisorControlDirectoryCleanupExecution(
            attempts=attempts,
            preflight=preflight,
            claims=claims,
            physical=physical,
            outcomes=attempts,
        )
        reconciliation = (
            ControlledManifestHandoffSupervisorControlDirectoryCleanupReconciliation(
                attempts=attempts,
                outcomes=attempts,
                physical=physical_reconciliation,
            )
        )
        return ManifestHandoffSupervisorControlDirectoryCleanupComposition(
            retention_operation=retention_operation,
            clearance_creation=clearance_creation,
            execution=execution,
            reconciliation=reconciliation,
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
