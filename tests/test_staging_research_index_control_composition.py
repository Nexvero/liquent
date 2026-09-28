from pathlib import Path

from sqlalchemy import event

from liquent_platform.application.staging_research_index_fixture_controller import (
    AuthorizedMembershipStagingResearchIndexFixtureController,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_changes import (
    DatabaseAuthorizedWorkspaceMembershipChanges,
)
from liquent_platform.persistence.staging_research_index_control_composition import (
    PersistentStagingResearchIndexFixtureControl,
    compose_persistent_staging_research_index_fixture_control,
)
from liquent_platform.persistence.staging_research_index_fixtures import (
    DatabaseStagingResearchIndexFixtures,
)


def test_composition_wires_one_engine_without_database_access(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda *args: statements.append(str(args[2])),
    )
    try:
        composed = compose_persistent_staging_research_index_fixture_control(engine)
        assert type(composed) is PersistentStagingResearchIndexFixtureControl
        assert type(composed.controller) is (
            AuthorizedMembershipStagingResearchIndexFixtureController
        )
        assert type(composed.resolver) is DatabaseStagingResearchIndexFixtures
        assert type(composed.changes) is DatabaseAuthorizedWorkspaceMembershipChanges
        assert statements == []
        assert repr(composed) == "PersistentStagingResearchIndexFixtureControl()"
    finally:
        engine.dispose()


def test_explicit_material_is_retained_but_not_exposed(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    material = SecureIdentityAuthorityMaterialGenerator()
    try:
        composed = compose_persistent_staging_research_index_fixture_control(
            engine, material=material
        )
        assert composed._material is material
        assert "material" not in repr(composed)
        assert not hasattr(composed, "execute")
    finally:
        engine.dispose()
