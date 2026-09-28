from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.application.staging_research_index_session_acquisition import (
    RegisteredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRegistryUnavailable,
    StagingResearchIndexSessionSetRevision,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_session_sets import DatabaseStagingResearchIndexSessionSets


SET_ID = StagingResearchIndexSessionSetId("persistent-session-set-2691")
REVISION = StagingResearchIndexSessionSetRevision("persistent-session-revision-2691")


def test_active_exact_revision_resolves_and_lifecycle_fails_closed(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'registry.db'}")
    upgrade_to_head(str(engine.url))
    registry = DatabaseStagingResearchIndexSessionSets(engine)
    try:
        assert registry.resolve(SET_ID, REVISION) is None
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO staging_research_index_session_sets VALUES (:i,:r,'active')"), {"i": SET_ID.value.encode(), "r": REVISION.value.encode()})
        assert registry.resolve(SET_ID, REVISION) == RegisteredStagingResearchIndexSessionSet(SET_ID, REVISION)
        with engine.begin() as connection:
            connection.execute(text("UPDATE staging_research_index_session_sets SET status='inactive'"))
        assert registry.resolve(SET_ID, REVISION) is None
    finally:
        engine.dispose()


def test_stale_revision_is_neutral_and_technical_failure_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    registry = DatabaseStagingResearchIndexSessionSets(engine)
    try:
        with pytest.raises(StagingResearchIndexSessionSetRegistryUnavailable) as raised:
            registry.resolve(SET_ID, REVISION)
        assert raised.value.__cause__ is None and raised.value.__context__ is None
        assert repr(registry) == "DatabaseStagingResearchIndexSessionSets()"
    finally:
        engine.dispose()
