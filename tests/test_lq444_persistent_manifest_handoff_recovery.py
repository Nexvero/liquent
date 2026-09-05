from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionEndId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffOwnershipConflict,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryEndId,
    ManifestHandoffRecoveryEndKind,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRecoveryRequest,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.manifest_handoff_execution import (
    DatabaseManifestHandoffExecutionOwnership,
)
from liquent_platform.persistence.manifest_handoff_observations import (
    DatabaseManifestHandoffObservationAppend,
)
from liquent_platform.persistence.manifest_handoff_recovery import (
    DatabaseManifestHandoffRecovery,
)
from liquent_platform.persistence.manifest_handoff_registry import (
    DatabaseManifestHandoffRegistry,
)
from liquent_platform.persistence.migrate import upgrade_to_head


NOW = datetime(2026, 8, 25, tzinfo=timezone.utc)
SCOPE = ManifestHandoffRegistryScopeId("scope-444")
ACTOR = UserId("actor-444")
ATTEMPT = ManifestHandoffAttemptId("attempt-444")
EXECUTION = ManifestHandoffExecutionClaimId("execution-444")
EXECUTION_OWNER = ManifestHandoffExecutionOwnerId("execution-owner-444")
RECOVERY = ManifestHandoffRecoveryClaimId("recovery-444")
RECOVERY_OWNER = ManifestHandoffRecoveryOwnerId("recovery-owner-444")
NAME = ManifestHandoffName("handoff-444")
FACTS = ManifestHandoffFacts("f" * 64, 5)


@pytest.fixture
def foundation(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'recovery.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)

    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,'active')"),
            {"actor": ACTOR.encode()},
        )
        connection.execute(
            text("INSERT INTO manifest_handoff_registry_scopes VALUES (:scope,'active')"),
            {"scope": SCOPE.value.encode()},
        )
        for table in (
            "manifest_handoff_registry_authorities",
            "manifest_handoff_recovery_authorities",
        ):
            connection.execute(
                text(f"INSERT INTO {table} VALUES (:scope,:actor,'active')"),
                {"scope": SCOPE.value.encode(), "actor": ACTOR.encode()},
            )
    registry = DatabaseManifestHandoffRegistry(
        engine,
        generate_attempt_id=lambda: ATTEMPT,
        generate_observation_id=lambda: ManifestHandoffObservationId("reserved-444"),
        clock=lambda: NOW,
    )
    registry.reserve_attempt(
        ManifestHandoffReservationId("reservation-444"), ACTOR, SCOPE, NAME
    )
    try:
        yield engine
    finally:
        engine.dispose()


def execution_store(engine):
    return DatabaseManifestHandoffExecutionOwnership(
        engine, lease_duration=timedelta(minutes=2), clock=lambda: NOW
    )


def recovery_store(engine, *, clock=lambda: NOW):
    return DatabaseManifestHandoffRecovery(engine, clock=clock)


def request(
    claim_id=RECOVERY, owner_id=RECOVERY_OWNER
) -> ManifestHandoffRecoveryRequest:
    return ManifestHandoffRecoveryRequest(claim_id, ACTOR, SCOPE, NAME, owner_id)


def prepare_unknown_execution(engine, *, started=True) -> None:
    store = execution_store(engine)
    store.claim_execution(EXECUTION, ATTEMPT, ACTOR, EXECUTION_OWNER)
    if started:
        store.start_claimed_execution(
            ManifestHandoffObservationId("started-444"), EXECUTION, EXECUTION_OWNER
        )
        store.record_outcome_unknown(
            ManifestHandoffExecutionEndId("execution-ended-444"),
            EXECUTION,
            EXECUTION_OWNER,
        )
    else:
        store.record_start_not_confirmed(
            ManifestHandoffExecutionEndId("execution-not-started-444"),
            EXECUTION,
            EXECUTION_OWNER,
        )


def test_new_claim_requires_explicit_current_recovery_authority(foundation) -> None:
    prepare_unknown_execution(foundation)
    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_recovery_authorities SET status='inactive'")
        )
    assert recovery_store(foundation).claim_recovery(request()) is None


def test_exact_claim_retry_survives_revocation_and_divergence_conflicts(foundation) -> None:
    prepare_unknown_execution(foundation)
    store = recovery_store(foundation)
    claimed = store.claim_recovery(request())
    assert claimed.execution_claim_id == EXECUTION
    assert claimed.writer_authorized is False
    assert claimed.cleanup_authorized is False
    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_recovery_authorities SET status='inactive'")
        )
    assert store.claim_recovery(request()) == claimed
    assert type(store.claim_recovery(request(
        owner_id=ManifestHandoffRecoveryOwnerId("other-owner-444")
    ))) is ManifestHandoffOwnershipConflict


def test_active_claim_serializes_recovery_and_resolved_outcome_needs_none(foundation) -> None:
    prepare_unknown_execution(foundation)
    store = recovery_store(foundation)
    store.claim_recovery(request())
    other = request(ManifestHandoffRecoveryClaimId("other-recovery-444"))
    assert store.claim_recovery(other) is None


@pytest.mark.parametrize(
    "method_name,kind,facts",
    (
        ("record_manifest_absent", ManifestHandoffObservationKind.MANIFEST_ABSENT, None),
        ("record_manifest_temporary_only", ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY, FACTS),
        ("record_manifest_handed_off", ManifestHandoffObservationKind.MANIFEST_HANDED_OFF, FACTS),
        ("record_manifest_handed_off_pending_cleanup", ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP, FACTS),
        ("record_manifest_handoff_conflict", ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT, None),
    ),
)
def test_five_reconciliation_sources_append_once_without_current_authority(
    foundation, method_name, kind, facts
) -> None:
    prepare_unknown_execution(foundation)
    store = recovery_store(foundation)
    store.claim_recovery(request())
    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_recovery_authorities SET status='inactive'")
        )
    observation_id = ManifestHandoffObservationId(f"reconciled-{kind.value}-444")
    arguments = (observation_id, RECOVERY, RECOVERY_OWNER)
    if facts is not None:
        arguments += (facts,)
    method = getattr(store, method_name)
    appended = method(*arguments)
    assert appended.observation.kind is kind
    assert appended.observation.facts == facts
    assert method(*arguments) == appended
    assert type(method(
        observation_id,
        RECOVERY,
        ManifestHandoffRecoveryOwnerId("wrong-owner-444"),
        *((facts,) if facts is not None else ()),
    )) is ManifestHandoffOwnershipConflict


def test_secured_end_requires_observation_and_atomically_releases_active_claim(foundation) -> None:
    prepare_unknown_execution(foundation)
    store = recovery_store(foundation)
    store.claim_recovery(request())
    assert store.record_outcome_secured(
        ManifestHandoffRecoveryEndId("too-early-444"), RECOVERY, RECOVERY_OWNER
    ) is None
    store.record_manifest_absent(
        ManifestHandoffObservationId("absent-444"), RECOVERY, RECOVERY_OWNER
    )
    end_id = ManifestHandoffRecoveryEndId("secured-444")
    ended = store.record_outcome_secured(end_id, RECOVERY, RECOVERY_OWNER)
    assert ended.kind is ManifestHandoffRecoveryEndKind.OUTCOME_SECURED
    assert store.record_outcome_secured(end_id, RECOVERY, RECOVERY_OWNER) == ended
    with foundation.connect() as connection:
        claim_ended, end_ended = connection.execute(text(
            "SELECT claim.ended_at,end_fact.ended_at"
            " FROM manifest_handoff_recovery_claims claim"
            " JOIN manifest_handoff_recovery_ends end_fact"
            " ON end_fact.claim_id=claim.claim_id"
        )).one()
    assert claim_ended == end_ended


def test_unknown_end_allows_new_claim_but_never_reuses_old_claim(foundation) -> None:
    prepare_unknown_execution(foundation)
    store = recovery_store(foundation)
    store.claim_recovery(request())
    ended = store.record_outcome_unknown(
        ManifestHandoffRecoveryEndId("unknown-444"), RECOVERY, RECOVERY_OWNER
    )
    assert ended.kind is ManifestHandoffRecoveryEndKind.OUTCOME_UNKNOWN
    second = request(
        ManifestHandoffRecoveryClaimId("recovery-two-444"),
        ManifestHandoffRecoveryOwnerId("recovery-owner-two-444"),
    )
    assert store.claim_recovery(second).claim_id == second.claim_id


def test_start_not_confirmed_execution_can_be_reconciled_without_writer_start(foundation) -> None:
    prepare_unknown_execution(foundation, started=False)
    store = recovery_store(foundation)
    store.claim_recovery(request())
    value = store.record_manifest_absent(
        ManifestHandoffObservationId("not-started-absent-444"),
        RECOVERY,
        RECOVERY_OWNER,
    )
    assert value.observation.sequence_number == 2
    assert value.observation.kind is ManifestHandoffObservationKind.MANIFEST_ABSENT


def test_already_durable_writer_success_is_not_recovered(foundation) -> None:
    execution = execution_store(foundation)
    execution.claim_execution(EXECUTION, ATTEMPT, ACTOR, EXECUTION_OWNER)
    execution.start_claimed_execution(
        ManifestHandoffObservationId("started-444"), EXECUTION, EXECUTION_OWNER
    )
    DatabaseManifestHandoffObservationAppend(foundation, clock=lambda: NOW).record_writer_handed_off(
        ManifestHandoffObservationId("writer-success-444"), ATTEMPT, FACTS
    )
    execution.record_outcome_secured(
        ManifestHandoffExecutionEndId("execution-secured-444"),
        EXECUTION,
        EXECUTION_OWNER,
    )
    assert recovery_store(foundation).claim_recovery(request()) is None


def test_roadmap_records_recovery_adapter_and_next_slice() -> None:
    roadmap = (Path(__file__).parents[1] / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-444 persistent manifest handoff recovery ownership:" in roadmap
    assert "`docs/lq-444-persistent-manifest-handoff-recovery-ownership.md`" in roadmap
    assert "nächster Slice LQ-445" in roadmap
