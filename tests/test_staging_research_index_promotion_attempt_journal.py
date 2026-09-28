from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionCommand,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    PreparedStagingResearchIndexPromotionAttempt,
    WriteStartedStagingResearchIndexPromotionAttempt,
)
from liquent_platform.application.staging_research_index_promotion_authority import (
    CurrentStagingResearchIndexPromotionAuthority,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (
    DatabaseStagingResearchIndexPromotionAttemptJournal,
    StagingResearchIndexPromotionAttemptJournalUnavailable,
)


NOW = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)


def _attempt(operation: str = "promotion-2708", actor: str = "user-2708"):
    principal = SessionPrincipal(UserId(actor))
    command = StagingResearchIndexPromotionCommand(principal, "sha256:" + "a" * 64)
    authority = CurrentStagingResearchIndexPromotionAuthority(
        principal.user_id,
        "sha256:" + "b" * 64,
        "https://staging.liquent.ai",
        "production",
    )
    return PreparedStagingResearchIndexPromotionAttempt(operation, command, authority)


@pytest.fixture
def journal(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'journal.db'}")
    upgrade_to_head(str(engine.url))
    yield engine, DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    engine.dispose()


def test_prepared_is_atomic_and_exact_retry_is_idempotent(journal) -> None:
    engine, store = journal
    attempt = _attempt()
    assert store.record_prepared(attempt, observed_at=NOW) is attempt
    assert store.record_prepared(attempt, observed_at=NOW) is attempt
    with engine.connect() as connection:
        attempts = connection.scalar(text(
            "SELECT count(*) FROM staging_research_index_promotion_attempts"
        ))
        events = connection.execute(text(
            "SELECT sequence,state FROM staging_research_index_promotion_attempt_events"
        )).all()
    assert attempts == 1
    assert events == [(1, "prepared")]


def test_same_operation_with_different_binding_fails_closed(journal) -> None:
    engine, store = journal
    store.record_prepared(_attempt(), observed_at=NOW)
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable) as caught:
        store.record_prepared(_attempt(actor="substituted"), observed_at=NOW)
    assert str(caught.value) == "staging_research_index_promotion_attempt_journal_unavailable"
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM staging_research_index_promotion_attempt_events"
        )) == 1


def test_write_started_requires_persisted_exact_prepared_and_is_idempotent(journal) -> None:
    engine, store = journal
    attempt = _attempt()
    store.record_prepared(attempt, observed_at=NOW)
    first = store.mark_write_started(attempt, observed_at=NOW)
    second = store.mark_write_started(attempt, observed_at=NOW)
    assert first.prepared is attempt
    assert second.prepared is attempt
    with engine.connect() as connection:
        states = connection.execute(text(
            "SELECT state FROM staging_research_index_promotion_attempt_events"
            " ORDER BY sequence"
        )).scalars().all()
    assert states == ["prepared", "write_started"]


def test_missing_or_substituted_prepared_attempt_cannot_start_write(journal) -> None:
    engine, store = journal
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable):
        store.mark_write_started(_attempt(), observed_at=NOW)
    store.record_prepared(_attempt(), observed_at=NOW)
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable):
        store.mark_write_started(_attempt(actor="substituted"), observed_at=NOW)
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM staging_research_index_promotion_attempt_events"
        )) == 1


def test_invalid_time_and_missing_schema_are_detail_free(tmp_path: Path, journal) -> None:
    _, store = journal
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable):
        store.record_prepared(_attempt(), observed_at=NOW.replace(tzinfo=None))
    engine = build_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    unavailable = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    try:
        with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable) as caught:
            unavailable.record_prepared(_attempt(), observed_at=NOW)
        assert str(caught.value) == "staging_research_index_promotion_attempt_journal_unavailable"
        assert repr(unavailable) == "DatabaseStagingResearchIndexPromotionAttemptJournal()"
        assert "sqlite" not in repr(unavailable)
    finally:
        engine.dispose()


def test_journal_exposes_no_outcome_or_retry_operation(journal) -> None:
    _, store = journal
    assert not hasattr(store, "record_committed")
    assert not hasattr(store, "retry")


def test_unknown_effect_requires_write_started_and_is_idempotent(journal) -> None:
    engine, store = journal
    prepared = _attempt()
    store.record_prepared(prepared, observed_at=NOW)
    started = store.mark_write_started(prepared, observed_at=NOW)
    first = store.record_unknown(started, observed_at=NOW)
    second = store.record_unknown(started, observed_at=NOW)
    assert first.attempt is started
    assert second.attempt is started
    with engine.connect() as connection:
        events = connection.execute(text(
            "SELECT sequence,state,provider_receipt_id"
            " FROM staging_research_index_promotion_attempt_events ORDER BY sequence"
        )).all()
    assert events == [
        (1, "prepared", None),
        (2, "write_started", None),
        (3, "effect_unknown", None),
    ]


def test_unknown_effect_rejects_missing_or_substituted_started_attempt(journal) -> None:
    engine, store = journal
    prepared = _attempt()
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable):
        store.record_unknown(
            WriteStartedStagingResearchIndexPromotionAttempt(prepared),
            observed_at=NOW,
        )
    store.record_prepared(prepared, observed_at=NOW)
    store.mark_write_started(prepared, observed_at=NOW)
    substituted = WriteStartedStagingResearchIndexPromotionAttempt(
        _attempt(actor="substituted")
    )
    with pytest.raises(StagingResearchIndexPromotionAttemptJournalUnavailable):
        store.record_unknown(substituted, observed_at=NOW)
    with engine.connect() as connection:
        states = connection.execute(text(
            "SELECT state FROM staging_research_index_promotion_attempt_events"
            " ORDER BY sequence"
        )).scalars().all()
    assert states == ["prepared", "write_started"]
