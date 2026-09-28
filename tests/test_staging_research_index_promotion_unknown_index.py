from pathlib import Path

import pytest

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (
    DatabaseStagingResearchIndexPromotionAttemptJournal,
)
from liquent_platform.persistence.staging_research_index_promotion_unknown_index import (
    DatabaseStagingResearchIndexPromotionUnknownIndex,
    StagingResearchIndexPromotionUnknownIndexUnavailable,
)
from tests.test_staging_research_index_promotion_attempt_journal import (
    NOW,
    _attempt,
    _receipt,
)


@pytest.fixture
def persistence(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'unknown-index.db'}")
    upgrade_to_head(str(engine.url))
    yield (
        engine,
        DatabaseStagingResearchIndexPromotionAttemptJournal(engine),
        DatabaseStagingResearchIndexPromotionUnknownIndex(engine),
    )
    engine.dispose()


def _unknown(journal, prepared):
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    return journal.record_unknown(started, observed_at=NOW)


def test_index_returns_only_current_unknown_operation_candidates(persistence) -> None:
    _, journal, index = persistence
    unknown = _attempt(operation="promotion-b")
    prepared = _attempt(operation="promotion-a")
    committed = _attempt(operation="promotion-c")
    journal.record_prepared(prepared, observed_at=NOW)
    _unknown(journal, unknown)
    journal.record_prepared(committed, observed_at=NOW)
    started = journal.mark_write_started(committed, observed_at=NOW)
    journal.record_committed(started, _receipt(committed), observed_at=NOW)
    assert index.list_unknown_operation_ids() == ("promotion-b",)
    assert repr(index) == "DatabaseStagingResearchIndexPromotionUnknownIndex()"


def test_reconciled_operation_disappears_on_next_read(persistence) -> None:
    _, journal, index = persistence
    prepared = _attempt(operation="promotion-2715")
    unknown = _unknown(journal, prepared)
    assert index.list_unknown_operation_ids() == (prepared.operation_id,)
    journal.record_reconciled_committed(unknown, _receipt(prepared), observed_at=NOW)
    assert index.list_unknown_operation_ids() == ()


def test_index_is_bounded_deterministic_and_read_only(persistence) -> None:
    _, journal, index = persistence
    for number in range(105):
        _unknown(journal, _attempt(operation=f"promotion-{number:03d}"))
    result = index.list_unknown_operation_ids()
    assert len(result) == 100
    assert result == tuple(f"promotion-{number:03d}" for number in range(100))
    assert not hasattr(index, "claim")
    assert not hasattr(index, "retry")
    assert not hasattr(index, "record_unknown")


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    index = DatabaseStagingResearchIndexPromotionUnknownIndex(engine)
    try:
        with pytest.raises(
            StagingResearchIndexPromotionUnknownIndexUnavailable
        ) as caught:
            index.list_unknown_operation_ids()
        assert caught.value.__cause__ is None and caught.value.__context__ is None
        assert "sqlite" not in str(caught.value)
    finally:
        engine.dispose()
