from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffName,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationConflict,
    ManifestHandoffReservationId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.manifest_handoff_registry import (
    DatabaseManifestHandoffRegistry,
)


NOW = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
SCOPE = ManifestHandoffRegistryScopeId("scope-432")
ACTOR = UserId("actor-432")
RESERVATION = ManifestHandoffReservationId("reservation-432")
ATTEMPT = ManifestHandoffAttemptId("attempt-432")
OBSERVATION = ManifestHandoffObservationId("observation-432")
NAME = ManifestHandoffName("handoff-432")


@pytest.fixture
def engine(tmp_path: Path):
    database = build_engine(f"sqlite:///{tmp_path / 'registry.db'}")

    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,'active')"),
            {"user": ACTOR.encode()},
        )
        connection.execute(
            text("INSERT INTO manifest_handoff_registry_scopes VALUES (:scope,'active')"),
            {"scope": SCOPE.value.encode()},
        )
        connection.execute(text(
            "INSERT INTO manifest_handoff_registry_authorities"
            " VALUES (:scope,:user,'active')"
        ), {"scope": SCOPE.value.encode(), "user": ACTOR.encode()})
    try:
        yield database
    finally:
        database.dispose()


def store(engine, *, attempt=lambda: ATTEMPT, observation=lambda: OBSERVATION):
    return DatabaseManifestHandoffRegistry(
        engine,
        generate_attempt_id=attempt,
        generate_observation_id=observation,
        clock=lambda: NOW,
    )


def test_reservation_atomically_persists_attempt_and_initial_observation(engine):
    result = store(engine).reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME)
    assert result.attempt_id == ATTEMPT
    assert result.reserved_at == NOW
    with engine.connect() as connection:
        attempt = connection.execute(text(
            "SELECT handoff_name,actor_user_id FROM manifest_handoff_attempts"
        )).one()
        observation = connection.execute(text(
            "SELECT sequence_number,kind,manifest_sha256,file_count"
            " FROM manifest_handoff_attempt_observations"
        )).one()
    assert attempt == (NAME.value, ACTOR.encode())
    assert observation == (1, "reserved", None, None)


def test_exact_retry_returns_same_attempt_without_generators_or_current_authority(engine):
    first = store(engine).reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME)
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE manifest_handoff_registry_authorities SET status='inactive'"
        ))
    fail = lambda: (_ for _ in ()).throw(RuntimeError("must not run"))
    assert store(engine, attempt=fail, observation=fail).reserve_attempt(
        RESERVATION, ACTOR, SCOPE, NAME
    ) == first


def test_divergent_retry_or_occupied_name_is_detail_free_conflict(engine):
    subject = store(engine)
    assert subject.reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME) is not None
    assert isinstance(subject.reserve_attempt(
        RESERVATION, ACTOR, SCOPE, ManifestHandoffName("other")
    ), ManifestHandoffReservationConflict)
    assert isinstance(subject.reserve_attempt(
        ManifestHandoffReservationId("other-reservation"), ACTOR, SCOPE, NAME
    ), ManifestHandoffReservationConflict)


@pytest.mark.parametrize("statement", [
    "UPDATE identity_users SET status='inactive'",
    "UPDATE manifest_handoff_registry_scopes SET status='inactive'",
    "UPDATE manifest_handoff_registry_authorities SET status='inactive'",
])
def test_inactive_current_facts_reject_new_reservation_and_lookup(engine, statement):
    assert store(engine).reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME) is not None
    with engine.begin() as connection:
        connection.execute(text(statement))
    assert store(engine).reserve_attempt(
        ManifestHandoffReservationId("new-reservation"), ACTOR, SCOPE,
        ManifestHandoffName("new-name"),
    ) is None
    assert store(engine).get_attempt(ACTOR, SCOPE, NAME) is None


def test_authorized_lookup_returns_latest_bounded_view(engine):
    subject = store(engine)
    subject.reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME)
    view = subject.get_attempt(ACTOR, SCOPE, NAME)
    assert view.attempt_id == ATTEMPT
    assert view.latest_observation is ManifestHandoffObservationKind.RESERVED
    assert view.handoff_name == NAME
    assert "actor-432" not in repr(view)


def test_missing_observation_is_unavailable_not_neutral_absence(engine):
    subject = store(engine)
    subject.reserve_attempt(RESERVATION, ACTOR, SCOPE, NAME)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM manifest_handoff_attempt_observations"))
    from liquent_platform.persistence.identity_errors import (
        ManifestHandoffRegistryUnavailable,
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        subject.get_attempt(ACTOR, SCOPE, NAME)


def test_roadmap_links_adapter_without_writer_or_entry_point_wiring():
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "- LQ-432 persistent authorized manifest handoff registry:" in roadmap
    assert "`docs/lq-432-persistent-authorized-manifest-handoff-registry.md`" in roadmap
    assert "nächster Slice LQ-433" in roadmap
    assert "manifest-handoff-registry" not in project
