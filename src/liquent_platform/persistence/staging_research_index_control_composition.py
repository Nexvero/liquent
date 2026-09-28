"""Side-effect-free composition of persistent staging fixture control."""

from dataclasses import dataclass

from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_fixture_controller import (
    AuthorizedMembershipStagingResearchIndexFixtureController,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.membership_changes import (
    DatabaseAuthorizedWorkspaceMembershipChanges,
)
from liquent_platform.persistence.staging_research_index_fixtures import (
    DatabaseStagingResearchIndexFixtures,
)


class _FixtureChangeIds:
    __slots__ = ("_material",)

    def __init__(self, material: SecureIdentityAuthorityMaterialGenerator) -> None:
        self._material = material

    def new_change_id(self):
        return self._material.new_workspace_membership_change_id()


@dataclass(frozen=True, slots=True)
class PersistentStagingResearchIndexFixtureControl:
    controller: AuthorizedMembershipStagingResearchIndexFixtureController
    resolver: DatabaseStagingResearchIndexFixtures
    changes: DatabaseAuthorizedWorkspaceMembershipChanges
    _material: SecureIdentityAuthorityMaterialGenerator

    def __repr__(self) -> str:
        return "PersistentStagingResearchIndexFixtureControl()"


def compose_persistent_staging_research_index_fixture_control(
    engine: Engine,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> PersistentStagingResearchIndexFixtureControl:
    """Wire persistent control without database access or execution startup."""

    source = material or SecureIdentityAuthorityMaterialGenerator()
    resolver = DatabaseStagingResearchIndexFixtures(engine)
    changes = DatabaseAuthorizedWorkspaceMembershipChanges(
        engine,
        generate_revision_id=source.new_workspace_membership_revision_id,
    )
    return PersistentStagingResearchIndexFixtureControl(
        controller=AuthorizedMembershipStagingResearchIndexFixtureController(
            resolver, changes, _FixtureChangeIds(source)
        ),
        resolver=resolver,
        changes=changes,
        _material=source,
    )
