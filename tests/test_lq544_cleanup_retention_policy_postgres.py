from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionOperationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention_policy import (
    BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
    ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId,
    ManifestHandoffSupervisorCleanupRetentionPolicyChangeId,
    ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent,
    ManifestHandoffSupervisorCleanupRetentionPolicyConflict,
    RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_retention_policy import (
    DatabaseManifestHandoffSupervisorCleanupRetentionPolicy,
)
from liquent_platform.application.manifest_handoff_supervisor_control_directory_cleanup_composition import (
    compose_manifest_handoff_supervisor_cleanup_retention_operation,
)
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_clearance_creation import (
    DatabaseManifestHandoffSupervisorCleanupClearanceCreation,
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
from liquent_platform.persistence.manifest_handoff_supervisor_journal import (
    DatabaseManifestHandoffSupervisorJournal,
)


pytestmark = pytest.mark.postgres_integration


def _b(value: str) -> bytes:
    return value.encode()


def _seed_retired_directory(engine: Engine, retired_at: datetime) -> tuple[UserId, ManifestHandoffSupervisorControlDirectoryId]:
    values = {
        "actor": _b("lq544-chain-actor"), "scope": _b("lq544-chain-scope"),
        "attempt": _b("lq544-chain-handoff"), "reservation": _b("lq544-chain-reservation"),
        "claim": _b("lq544-chain-claim"), "owner": _b("lq544-chain-owner"),
        "backend": _b("lq544-chain-backend"), "prepare": _b("lq544-chain-prepare"),
        "handle": _b("lq544-chain-handle"), "launch": _b("lq544-chain-launch"),
        "terminal": _b("lq544-chain-terminal"), "directory": _b("lq544-chain-directory"),
        "leaf": "b" * 64, "management": _b("lq544-chain-management"),
        "hold": _b("lq544-chain-hold"), "recovery": _b("lq544-chain-recovery"),
        "reference": _b("lq544-chain-reference"),
        "t0": retired_at - timedelta(seconds=3), "t1": retired_at - timedelta(seconds=2),
        "t2": retired_at, "t3": retired_at + timedelta(seconds=1),
    }
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users (user_id,status) VALUES (:actor,'active')"), values)
        connection.execute(text("INSERT INTO manifest_handoff_registry_scopes (scope_id,status) VALUES (:scope,'active')"), values)
        connection.execute(text("INSERT INTO manifest_handoff_attempts (attempt_id,reservation_id,scope_id,actor_user_id,handoff_name,reserved_at) VALUES (:attempt,:reservation,:scope,:actor,'lq544-chain',:t0)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_execution_claims (claim_id,attempt_id,actor_user_id,owner_id,claimed_at,lease_expires_at) VALUES (:claim,:attempt,:actor,:owner,:t0,:t3)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_backends (backend_instance_id,status,provisioned_at) VALUES (:backend,'active',:t0)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_preparations (prepare_id,backend_instance_id,capability,execution_claim_id,recovery_claim_id,owner_id,reserved_at) VALUES (:prepare,:backend,'writer',:claim,NULL,:owner,:t0)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_handle_bindings (handle_id,prepare_id,backend_instance_id,bound_at) VALUES (:handle,:prepare,:backend,:t0)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_terminal_observations (terminal_observation_id,handle_id,observed_at) VALUES (:terminal,:handle,:t3)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_journal_jobs (handle_id,backend_instance_id,prepare_id,launch_commit_id,capability,execution_claim_id,recovery_claim_id,owner_id,scope_id,source_root,target_root,handoff_name,registered_at) VALUES (:handle,:backend,:prepare,:launch,'writer',:claim,NULL,:owner,:scope,'/source','/target','lq544-chain',:t0)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_journal_transitions (transition_id,handle_id,capability,sequence_number,kind,outcome_kind,filename,manifest_sha256,file_count,observed_at) VALUES (:launch,:handle,'writer',1,'launch_committed',NULL,NULL,NULL,NULL,:t1),(:terminal,:handle,'writer',2,'terminal_observed','unavailable',NULL,NULL,NULL,:t3)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_control_directories (directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at) VALUES (:directory,:handle,:leaf,'retired',:t0,:t1,:t2)"), values)
        connection.execute(text("INSERT INTO manifest_handoff_supervisor_cleanup_management_revisions (revision_id,actor_user_id,scope_id,sequence_number,status,resolved_at) VALUES (:management,:actor,:scope,1,'active',:t3)"), values)
        for kind in ("hold", "recovery", "reference"):
            connection.execute(text(f"INSERT INTO manifest_handoff_supervisor_cleanup_{kind}_revisions (revision_id,directory_id,sequence_number,disposition,decided_at) VALUES (:{kind},:directory,1,'clear',:t3)"), values)
    return UserId("lq544-chain-actor"), ManifestHandoffSupervisorControlDirectoryId("lq544-chain-directory")


def test_policy_bootstrap_mutation_lifecycle_revocation_and_recovery(
    postgres_engine: Engine,
) -> None:
    times = iter(datetime(2026, 8, 27, tzinfo=timezone.utc) + timedelta(seconds=i)
                 for i in range(20))
    policies = iter(f"lq544-policy-{i}" for i in range(5))
    authorities = iter(f"lq544-authority-{i}" for i in range(10))
    store = DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(
        postgres_engine, clock=lambda: next(times),
        policy_revision_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(next(policies)),
        authority_revision_generator=lambda: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(next(authorities)),
    )
    first, second = UserId("lq544-user-a"), UserId("lq544-user-b")
    with postgres_engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users (user_id,status) VALUES (:a,'active'),(:b,'active')"),
                           {"a": _b(first), "b": _b(second)})
    bootstrap = BootstrapManifestHandoffSupervisorCleanupRetentionPolicy(
        ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId("lq544-bootstrap"),
        first, timedelta(seconds=60))
    initial = store.bootstrap_cleanup_retention_policy(bootstrap)
    assert initial.active_policy.policy.minimum_retention == timedelta(seconds=60)
    assert store.bootstrap_cleanup_retention_policy(bootstrap) == initial
    principal = SessionPrincipal(first)
    assert store.permits_cleanup_retention_policy_mutation(principal) is True

    shortened = ChangeManifestHandoffSupervisorCleanupRetentionPolicy(
        ManifestHandoffSupervisorCleanupRetentionPolicyChangeId("lq544-short"),
        initial.active_policy.policy.revision_id,
        ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent.REPLACE,
        timedelta(seconds=59))
    assert type(store.change_cleanup_retention_policy(principal, shortened)) is ManifestHandoffSupervisorCleanupRetentionPolicyConflict
    replacement = ChangeManifestHandoffSupervisorCleanupRetentionPolicy(
        ManifestHandoffSupervisorCleanupRetentionPolicyChangeId("lq544-replace"),
        initial.active_policy.policy.revision_id,
        ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent.REPLACE,
        timedelta(seconds=120))
    changed = store.change_cleanup_retention_policy(principal, replacement)
    assert changed.active_policy.policy.minimum_retention == timedelta(seconds=120)
    assert store.change_cleanup_retention_policy(principal, replacement) == changed

    grant = ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority(
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId("lq544-grant"), second,
        initial.authority_set.revision_id,
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent.GRANT)
    granted = store.change_cleanup_retention_policy_authority(principal, grant)
    deactivate = ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority(
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId("lq544-deactivate"), first,
        granted.revision_id,
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent.DEACTIVATE)
    deactivated = store.change_cleanup_retention_policy_authority(principal, deactivate)
    assert store.permits_cleanup_retention_policy_mutation(principal) is False
    with postgres_engine.begin() as connection:
        connection.execute(text("UPDATE identity_users SET status='inactive' WHERE user_id=:user"),
                           {"user": _b(second)})
    recovery = RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority(
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId("lq544-recovery"),
        first, deactivated.revision_id)
    recovered = store.recover_cleanup_retention_policy_authority(recovery)
    assert recovered.revision_id != deactivated.revision_id
    assert store.recover_cleanup_retention_policy_authority(recovery) == recovered
    assert store.permits_cleanup_retention_policy_mutation(principal) is True


def test_migration_head_contains_empty_closed_policy_foundation(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        counts = connection.execute(text(
            "SELECT (SELECT count(*) FROM mh_supervisor_cleanup_retention_policy_revisions),"
            "(SELECT count(*) FROM mh_supervisor_cleanup_retention_policy_authority_sets),"
            "(SELECT count(*) FROM mh_supervisor_cleanup_retention_policy_bootstraps)"
        )).one()
    assert tuple(counts) == (0, 0, 0)


def test_retention_operation_retry_and_policy_replacement_revoke_clearance(
    postgres_engine: Engine,
) -> None:
    retired_at = datetime(2026, 8, 20, tzinfo=timezone.utc)
    now = retired_at + timedelta(seconds=10)
    actor, directory_id = _seed_retired_directory(postgres_engine, retired_at)
    policies = DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(
        postgres_engine, clock=lambda: now,
        policy_revision_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId("lq544-chain-policy-a"),
        authority_revision_generator=lambda: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId("lq544-chain-authority"),
    )
    initial = policies.bootstrap_cleanup_retention_policy(
        BootstrapManifestHandoffSupervisorCleanupRetentionPolicy(
            ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId("lq544-chain-bootstrap"),
            actor, timedelta(seconds=5),
        )
    )
    operation = compose_manifest_handoff_supervisor_cleanup_retention_operation(
        database_engine=postgres_engine, clock=lambda: now,
    )
    evaluation_request = EvaluateManifestHandoffSupervisorControlDirectoryRetention(
        ManifestHandoffSupervisorCleanupRetentionOperationId("lq544-chain-operation"),
        directory_id,
    )
    bound = operation.execute(evaluation_request)
    assert bound.decision.policy_revision_id == initial.active_policy.policy.revision_id
    assert operation.execute(evaluation_request) == bound
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM manifest_handoff_supervisor_control_cleanup_decisions"
        )) == 1

    cleanup_request = CleanupManifestHandoffSupervisorControlDirectory(
        ManifestHandoffSupervisorControlDirectoryCleanupAttemptId("lq544-chain-cleanup"),
        actor, directory_id,
    )
    creation = DatabaseManifestHandoffSupervisorCleanupClearanceCreation(
        postgres_engine, clock=lambda: now + timedelta(seconds=1),
        clearance_id_generator=lambda: "lq544-chain-clearance",
    )
    clearance = creation.create_control_directory_cleanup_clearance(
        SessionPrincipal(actor), cleanup_request,
    )
    assert clearance.decision.decision_id == bound.decision.decision_id

    directories = DatabaseManifestHandoffSupervisorControlDirectories(postgres_engine)
    decisions = DatabaseManifestHandoffSupervisorControlDirectoryCleanup(postgres_engine)
    journal = DatabaseManifestHandoffSupervisorJournal(
        postgres_engine,
        backend_instance_id=ManifestHandoffSupervisorBackendInstanceId("lq544-chain-backend"),
    )
    resolver = DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance(
        postgres_engine, directory_lookup=directories, decision_lookup=decisions,
        writer_journal_lookup=journal.inspect_writer_journal,
        recovery_journal_lookup=journal.inspect_recovery_journal,
    )
    assert resolver.resolve_control_directory_cleanup_clearance(cleanup_request) == clearance

    replacement = DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(
        postgres_engine, clock=lambda: now + timedelta(seconds=2),
        policy_revision_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId("lq544-chain-policy-b"),
        authority_revision_generator=lambda: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId("unused"),
    ).change_cleanup_retention_policy(
        SessionPrincipal(actor),
        ChangeManifestHandoffSupervisorCleanupRetentionPolicy(
            ManifestHandoffSupervisorCleanupRetentionPolicyChangeId("lq544-chain-replace"),
            initial.active_policy.policy.revision_id,
            ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent.REPLACE,
            timedelta(seconds=6),
        ),
    )
    assert replacement.active_policy.policy.revision_id.value == "lq544-chain-policy-b"
    assert type(resolver.resolve_control_directory_cleanup_clearance(cleanup_request)) is ManifestHandoffSupervisorControlDirectoryCleanupConflict
    assert type(creation.create_control_directory_cleanup_clearance(SessionPrincipal(actor), cleanup_request)) is ManifestHandoffSupervisorControlDirectoryCleanupConflict
