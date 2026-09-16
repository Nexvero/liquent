from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (
    DatabaseStagingResearchIndexPromotionAttemptJournal,
)
from liquent_platform.persistence.staging_research_index_promotion_unknown_reader import (
    DatabaseStagingResearchIndexPromotionUnknownReader,
    StagingResearchIndexPromotionUnknownReaderUnavailable,
)
from tests.test_staging_research_index_promotion_attempt_journal import (
    NOW,
    _attempt,
    _receipt,
)


@pytest.fixture
def persistence(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'unknown-reader.db'}")
    upgrade_to_head(str(engine.url))
    yield (
        engine,
        DatabaseStagingResearchIndexPromotionAttemptJournal(engine),
        DatabaseStagingResearchIndexPromotionUnknownReader(engine),
    )
    engine.dispose()


def test_exact_durable_unknown_attempt_is_reconstructed(persistence) -> None:
    _, journal, reader = persistence
    prepared = _attempt()
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    journal.record_unknown(started, observed_at=NOW)
    unknown = reader.resolve_unknown(prepared.operation_id)
    assert unknown is not None
    restored = unknown.attempt.prepared
    assert restored.operation_id == prepared.operation_id
    assert restored.command == prepared.command
    assert restored.authority == prepared.authority
    assert repr(reader) == "DatabaseStagingResearchIndexPromotionUnknownReader()"


def test_absent_incomplete_and_directly_committed_attempts_are_neutral(persistence) -> None:
    _, journal, reader = persistence
    prepared = _attempt()
    assert reader.resolve_unknown(prepared.operation_id) is None
    journal.record_prepared(prepared, observed_at=NOW)
    assert reader.resolve_unknown(prepared.operation_id) is None
    started = journal.mark_write_started(prepared, observed_at=NOW)
    assert reader.resolve_unknown(prepared.operation_id) is None
    journal.record_committed(started, _receipt(prepared), observed_at=NOW)
    assert reader.resolve_unknown(prepared.operation_id) is None


def test_reconciled_unknown_is_no_longer_resolved(persistence) -> None:
    _, journal, reader = persistence
    prepared = _attempt()
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    unknown = journal.record_unknown(started, observed_at=NOW)
    assert reader.resolve_unknown(prepared.operation_id) is not None
    journal.record_reconciled_committed(unknown, _receipt(prepared), observed_at=NOW)
    assert reader.resolve_unknown(prepared.operation_id) is None


def test_malformed_history_and_technical_failure_are_detail_free(persistence, tmp_path) -> None:
    engine, journal, reader = persistence
    prepared = _attempt()
    journal.record_prepared(prepared, observed_at=NOW)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO staging_research_index_promotion_attempt_events"
            " (operation_id,sequence,state,provider_receipt_id,observed_at)"
            " VALUES (:operation,4,'effect_unknown',NULL,:observed)"
        ), {"operation": prepared.operation_id, "observed": "2026-09-16T08:00:00Z"})
    with pytest.raises(StagingResearchIndexPromotionUnknownReaderUnavailable):
        reader.resolve_unknown(prepared.operation_id)

    empty = build_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    broken = DatabaseStagingResearchIndexPromotionUnknownReader(empty)
    try:
        with pytest.raises(StagingResearchIndexPromotionUnknownReaderUnavailable) as caught:
            broken.resolve_unknown("promotion-2713")
        assert caught.value.__cause__ is None and caught.value.__context__ is None
        assert "sqlite" not in str(caught.value)
    finally:
        empty.dispose()


def test_reader_exposes_no_mutation_or_retry_capability(persistence) -> None:
    _, _, reader = persistence
    assert not hasattr(reader, "record_unknown")
    assert not hasattr(reader, "record_committed")
    assert not hasattr(reader, "retry")
    with pytest.raises(StagingResearchIndexPromotionUnknownReaderUnavailable):
        reader.resolve_unknown("not valid")
