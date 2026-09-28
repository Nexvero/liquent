from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionEndId,
    ManifestHandoffExecutionEndKind,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts,
    ManifestHandoffLeaseRenewalId,
    ManifestHandoffName,
    ManifestHandoffObservationId,
    ManifestHandoffOwnershipConflict,
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
from liquent_platform.persistence.manifest_handoff_registry import (
    DatabaseManifestHandoffRegistry,
)
from liquent_platform.persistence.migrate import upgrade_to_head


NOW = datetime(2026, 8, 24, 22, tzinfo=timezone.utc)
SCOPE = ManifestHandoffRegistryScopeId("scope-443")
ACTOR = UserId("actor-443")
ATTEMPT = ManifestHandoffAttemptId("attempt-443")
CLAIM = ManifestHandoffExecutionClaimId("claim-443")
OWNER = ManifestHandoffExecutionOwnerId("owner-443")


@pytest.fixture
def foundation(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'execution.db'}"
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
        connection.execute(
            text("INSERT INTO manifest_handoff_registry_authorities VALUES (:scope,:actor,'active')"),
            {"scope": SCOPE.value.encode(), "actor": ACTOR.encode()},
        )
    registry = DatabaseManifestHandoffRegistry(
        engine,
        generate_attempt_id=lambda: ATTEMPT,
        generate_observation_id=lambda: ManifestHandoffObservationId("reserved-443"),
        clock=lambda: NOW,
    )
    registry.reserve_attempt(
        ManifestHandoffReservationId("reservation-443"),
        ACTOR,
        SCOPE,
        ManifestHandoffName("handoff-443"),
    )
    try:
        yield engine
    finally:
        engine.dispose()


def subject(engine, *, clock=lambda: NOW):
    return DatabaseManifestHandoffExecutionOwnership(
        engine, lease_duration=timedelta(minutes=2), clock=clock
    )


def claim(subject):
    return subject.claim_execution(CLAIM, ATTEMPT, ACTOR, OWNER)


def start(subject, value="started-443"):
    return subject.start_claimed_execution(
        ManifestHandoffObservationId(value), CLAIM, OWNER
    )


def test_claim_requires_current_authority_and_is_permanent_per_attempt(foundation) -> None:
    store = subject(foundation)
    value = claim(store)
    assert value.attempt_id == ATTEMPT
    assert value.writer_authorized is False
    assert value.lease_expires_at == NOW + timedelta(minutes=2)

    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_registry_authorities SET status='inactive'")
        )
    assert claim(store) == value
    assert type(store.claim_execution(
        ManifestHandoffExecutionClaimId("other-claim-443"), ATTEMPT, ACTOR, OWNER
    )) is ManifestHandoffOwnershipConflict


def test_revocation_before_new_claim_or_claimed_start_fails_closed(foundation) -> None:
    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_registry_authorities SET status='inactive'")
        )
    assert claim(subject(foundation)) is None

    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_registry_authorities SET status='active'")
        )
    store = subject(foundation)
    claim(store)
    with foundation.begin() as connection:
        connection.execute(
            text("UPDATE manifest_handoff_registry_authorities SET status='inactive'")
        )
    assert start(store) is None
    with foundation.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM manifest_handoff_attempt_observations"
            " WHERE kind='writer_started'"
        )) == 0


def test_claimed_start_atomically_binds_claim_observation_and_attempt(foundation) -> None:
    store = subject(foundation)
    claim(store)
    value = start(store)
    assert value.claim_id == CLAIM and value.attempt_id == ATTEMPT
    assert start(store) == value
    assert type(store.start_claimed_execution(
        ManifestHandoffObservationId("other-start-443"), CLAIM, OWNER
    )) is ManifestHandoffOwnershipConflict
    with foundation.connect() as connection:
        row = connection.execute(text(
            "SELECT observation.kind,observation.attempt_id,start.owner_id"
            " FROM manifest_handoff_execution_starts start"
            " JOIN manifest_handoff_attempt_observations observation"
            " ON observation.observation_id=start.observation_id"
        )).one()
    assert row.kind == "writer_started"
    assert row.attempt_id == ATTEMPT.value.encode()
    assert row.owner_id == OWNER.value.encode()


def test_lease_renewal_is_retry_safe_and_does_not_authorize_recovery(foundation) -> None:
    store = subject(foundation, clock=lambda: NOW + timedelta(hours=1))
    claim(subject(foundation))
    renewal_id = ManifestHandoffLeaseRenewalId("renewal-443")
    value = store.renew_execution_lease(renewal_id, CLAIM, OWNER)
    assert value.recovery_authorized is False
    assert value.renewed_at == NOW + timedelta(hours=1)
    assert store.renew_execution_lease(renewal_id, CLAIM, OWNER) == value
    assert type(store.renew_execution_lease(
        renewal_id, CLAIM, ManifestHandoffExecutionOwnerId("other-owner-443")
    )) is ManifestHandoffOwnershipConflict


def test_terminal_sources_require_matching_started_state(foundation) -> None:
    store = subject(foundation)
    claim(store)
    assert store.record_outcome_unknown(
        ManifestHandoffExecutionEndId("premature-443"), CLAIM, OWNER
    ) is None
    not_started = store.record_start_not_confirmed(
        ManifestHandoffExecutionEndId("not-started-443"), CLAIM, OWNER
    )
    assert not_started.kind is ManifestHandoffExecutionEndKind.START_NOT_CONFIRMED
    assert store.renew_execution_lease(
        ManifestHandoffLeaseRenewalId("late-renewal-443"), CLAIM, OWNER
    ) is None


def test_secured_end_requires_durable_outcome_and_exact_retry(foundation) -> None:
    store = subject(foundation)
    claim(store)
    start(store)
    assert store.record_outcome_secured(
        ManifestHandoffExecutionEndId("too-early-443"), CLAIM, OWNER
    ) is None
    DatabaseManifestHandoffObservationAppend(foundation, clock=lambda: NOW).record_writer_handed_off(
        ManifestHandoffObservationId("outcome-443"),
        ATTEMPT,
        ManifestHandoffFacts("e" * 64, 4),
    )
    end_id = ManifestHandoffExecutionEndId("secured-443")
    ended = store.record_outcome_secured(end_id, CLAIM, OWNER)
    assert ended.kind is ManifestHandoffExecutionEndKind.OUTCOME_SECURED
    assert store.record_outcome_secured(end_id, CLAIM, OWNER) == ended
    assert type(store.record_outcome_unknown(end_id, CLAIM, OWNER)) is ManifestHandoffOwnershipConflict


def test_roadmap_records_adapter_and_next_slice() -> None:
    roadmap = (Path(__file__).parents[1] / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-443 persistent manifest handoff execution ownership:" in roadmap
    assert "`docs/lq-443-persistent-manifest-handoff-execution-ownership.md`" in roadmap
    assert "nächster Slice LQ-444" in roadmap
