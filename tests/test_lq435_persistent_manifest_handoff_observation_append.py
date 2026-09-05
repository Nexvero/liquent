from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.manifest_handoff_observations import (
    DatabaseManifestHandoffObservationAppend,
)
from liquent_platform.persistence.manifest_handoff_registry import (
    DatabaseManifestHandoffRegistry,
)
from liquent_platform.persistence.migrate import upgrade_to_head


NOW = datetime(2026, 8, 24, 16, tzinfo=timezone.utc)
SCOPE = ManifestHandoffRegistryScopeId("scope-435")
ACTOR = UserId("actor-435")
ATTEMPT = ManifestHandoffAttemptId("attempt-435")
NAME = ManifestHandoffName("handoff-435")
FACTS = ManifestHandoffFacts("b" * 64, 2)


@pytest.fixture
def engine(tmp_path: Path):
    database = build_engine(f"sqlite:///{tmp_path / 'observations.db'}")

    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (:u,'active')"), {"u": ACTOR.encode()})
        connection.execute(text("INSERT INTO manifest_handoff_registry_scopes VALUES (:s,'active')"), {"s": SCOPE.value.encode()})
        connection.execute(text("INSERT INTO manifest_handoff_registry_authorities VALUES (:s,:u,'active')"), {"s": SCOPE.value.encode(), "u": ACTOR.encode()})
    registry = DatabaseManifestHandoffRegistry(
        database,
        generate_attempt_id=lambda: ATTEMPT,
        generate_observation_id=lambda: ManifestHandoffObservationId("reserved-435"),
        clock=lambda: NOW,
    )
    registry.reserve_attempt(
        ManifestHandoffReservationId("reservation-435"), ACTOR, SCOPE, NAME
    )
    try:
        yield database
    finally:
        database.dispose()


def subject(engine, clock=lambda: NOW):
    return DatabaseManifestHandoffObservationAppend(engine, clock=clock)


def observation(value: str) -> ManifestHandoffObservationId:
    return ManifestHandoffObservationId(value)


def test_writer_start_requires_current_authority_and_is_single_use(engine):
    value = subject(engine).record_writer_started(observation("start"), ATTEMPT)
    assert value.sequence_number == 2
    assert subject(engine).record_writer_started(observation("second"), ATTEMPT) is None

    with engine.begin() as connection:
        connection.execute(text("UPDATE manifest_handoff_registry_authorities SET status='inactive'"))
    assert subject(engine).record_writer_outcome_unknown(
        observation("unknown"), ATTEMPT
    ).sequence_number == 3


def test_inactive_authority_blocks_start_without_clock(engine):
    with engine.begin() as connection:
        connection.execute(text("UPDATE identity_users SET status='inactive'"))
    fail = lambda: (_ for _ in ()).throw(RuntimeError("clock must not run"))
    assert subject(engine, fail).record_writer_started(observation("start"), ATTEMPT) is None


def test_exact_retry_is_stable_and_divergent_reuse_conflicts(engine):
    append = subject(engine)
    oid = observation("start")
    first = append.record_writer_started(oid, ATTEMPT)
    fail = lambda: (_ for _ in ()).throw(RuntimeError("clock must not run"))
    assert subject(engine, fail).record_writer_started(oid, ATTEMPT) == first
    conflict = subject(engine).record_manifest_absent(oid, ATTEMPT)
    assert isinstance(conflict, ManifestHandoffObservationConflict)


def test_reconciliation_and_cleanup_follow_transition_matrix(engine):
    append = subject(engine)
    assert append.record_manifest_absent(observation("early"), ATTEMPT) is None
    append.record_writer_started(observation("start"), ATTEMPT)
    pending = append.record_manifest_handed_off_pending_cleanup(
        observation("pending"), ATTEMPT, FACTS
    )
    assert pending.sequence_number == 3
    cleaned = append.record_cleanup_completed(observation("cleaned"), ATTEMPT, FACTS)
    assert cleaned.sequence_number == 4
    reconciled = append.record_manifest_handed_off(
        observation("reconciled"), ATTEMPT, FACTS
    )
    assert reconciled.sequence_number == 5


def test_broken_history_is_unavailable_not_neutral(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE manifest_handoff_attempt_observations"
            " SET kind='writer_started' WHERE sequence_number=1"
        ))
    from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject(engine).record_writer_started(observation("start"), ATTEMPT)


def test_impossible_but_well_formed_history_is_unavailable(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO manifest_handoff_attempt_observations"
            " VALUES (:o,:a,2,'cleanup_completed',:d,:c,:n)"
        ), {
            "o": b"impossible-435", "a": ATTEMPT.value.encode(),
            "d": FACTS.manifest_sha256, "c": FACTS.file_count, "n": NOW,
        })
    from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject(engine).record_manifest_handed_off(
            observation("later"), ATTEMPT, FACTS
        )


def test_roadmap_links_adapter_without_composition_or_migration():
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-435 persistent manifest handoff observation append:" in roadmap
    assert "`docs/lq-435-persistent-manifest-handoff-observation-append.md`" in roadmap
    assert "nächster Slice LQ-436" in roadmap
