"""Read-only persistent staging Research-index session-set registry."""

from sqlalchemy import Engine, text

from liquent_platform.application.staging_research_index_session_acquisition import (
    RegisteredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRegistryUnavailable,
    StagingResearchIndexSessionSetRevision,
)


_SELECT = text(
    "SELECT session_set_id,revision_id FROM staging_research_index_session_sets"
    " WHERE session_set_id=:session_set AND revision_id=:revision AND status='active'"
)


class DatabaseStagingResearchIndexSessionSets:
    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexSessionSets()"

    def resolve(self, session_set_id, expected_revision):
        try:
            if (
                type(session_set_id) is not StagingResearchIndexSessionSetId
                or type(expected_revision) is not StagingResearchIndexSessionSetRevision
            ):
                raise StagingResearchIndexSessionSetRegistryUnavailable
            with self._engine.connect() as connection:
                rows = connection.execute(_SELECT, {
                    "session_set": session_set_id.value.encode(),
                    "revision": expected_revision.value.encode(),
                }).all()
            if not rows:
                return None
            if len(rows) != 1 or rows[0].session_set_id != session_set_id.value.encode() or rows[0].revision_id != expected_revision.value.encode():
                raise StagingResearchIndexSessionSetRegistryUnavailable
            return RegisteredStagingResearchIndexSessionSet(session_set_id, expected_revision)
        except StagingResearchIndexSessionSetRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexSessionSetRegistryUnavailable from None
