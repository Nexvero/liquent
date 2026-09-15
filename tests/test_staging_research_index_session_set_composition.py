from pathlib import Path

from sqlalchemy import event

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.staging_research_index_session_set_composition import (
    PersistentStagingResearchIndexSessionSetRegistry,
    compose_persistent_staging_research_index_session_set_registry,
)
from liquent_platform.persistence.staging_research_index_session_sets import (
    DatabaseStagingResearchIndexSessionSets,
)


def test_composition_binds_one_engine_without_database_io(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    statements: list[str] = []
    event.listen(engine, "before_cursor_execute", lambda *args: statements.append(str(args[2])))
    try:
        composed = compose_persistent_staging_research_index_session_set_registry(engine)
        assert type(composed) is PersistentStagingResearchIndexSessionSetRegistry
        assert type(composed.resolver) is DatabaseStagingResearchIndexSessionSets
        assert statements == []
        assert not (tmp_path / "absent.db").exists()
        assert repr(composed) == "PersistentStagingResearchIndexSessionSetRegistry()"
    finally:
        engine.dispose()


def test_composition_exposes_no_mutation_or_acquisition_capability(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    try:
        composed = compose_persistent_staging_research_index_session_set_registry(engine)
        for name in ("create", "update", "delete", "rotate", "acquire", "execute"):
            assert not hasattr(composed, name)
    finally:
        engine.dispose()
