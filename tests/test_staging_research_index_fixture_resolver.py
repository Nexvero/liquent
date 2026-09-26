from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
)
from liquent_platform.application.staging_research_index_fixture_controller import (
    ResolvedStagingResearchIndexFixture,
    StagingResearchIndexFixtureControlUnavailable,
    StagingResearchIndexFixtureResolver,
)
from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import WorkspaceMembershipRevisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_fixtures import (
    DatabaseStagingResearchIndexFixtures,
)

FIXTURE = StagingResearchIndexFixtureId("fixture-research-index-2684")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'fixture.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _seed(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (X'61','active')"))
        connection.execute(text("INSERT INTO identity_users VALUES (X'74','active')"))
        connection.execute(text("INSERT INTO identity_workspaces VALUES (X'77','active')"))
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities"
            " VALUES (X'61',X'77','active')"
        ))
        connection.execute(text(
            "INSERT INTO workspace_membership_revisions VALUES"
            " (X'7265762D616374697665',X'74',X'77','active')"
        ))
        connection.execute(text(
            "INSERT INTO workspace_membership_revision_permissions VALUES"
            " (X'7265762D616374697665','research:read'),"
            " (X'7265762D616374697665','research:write')"
        ))
        connection.execute(text(
            "INSERT INTO staging_research_index_fixtures VALUES"
            " (:fixture,X'61',X'74',X'77',X'7265762D616374697665')"
        ), {"fixture": FIXTURE.value.encode()})


def test_resolves_exact_authoritative_binding(engine: Engine) -> None:
    _seed(engine)
    resolver: StagingResearchIndexFixtureResolver = (
        DatabaseStagingResearchIndexFixtures(engine)
    )
    assert resolver.resolve(FIXTURE) == ResolvedStagingResearchIndexFixture(
        FIXTURE, SessionPrincipal(UserId("a")), UserId("t"), WorkspaceId("w"),
        WorkspaceMembershipRevisionId("rev-active"), MembershipStatus.ACTIVE,
        frozenset({Permission.RESEARCH_READ, Permission.RESEARCH_WRITE}),
    )


def test_original_snapshot_remains_resolvable_after_current_revision_moves(
    engine: Engine,
) -> None:
    _seed(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_memberships"
            " (user_id,workspace_id,status,revision_id)"
            " VALUES (X'74',X'77','inactive',NULL)"
        ))
    assert DatabaseStagingResearchIndexFixtures(engine).resolve(FIXTURE) is not None


@pytest.mark.parametrize("statement", [
    "UPDATE identity_users SET status='inactive' WHERE user_id=X'61'",
    "UPDATE identity_users SET status='inactive' WHERE user_id=X'74'",
    "UPDATE identity_workspaces SET status='inactive' WHERE workspace_id=X'77'",
    "UPDATE workspace_membership_management_authorities SET status='inactive'",
])
def test_lifecycle_or_authority_revocation_affects_later_resolution(
    engine: Engine, statement: str
) -> None:
    _seed(engine)
    resolver = DatabaseStagingResearchIndexFixtures(engine)
    assert resolver.resolve(FIXTURE) is not None
    with engine.begin() as connection:
        connection.execute(text(statement))
    assert resolver.resolve(FIXTURE) is None


def test_absence_is_neutral_and_technical_failure_is_detail_free(
    engine: Engine, tmp_path: Path
) -> None:
    resolver = DatabaseStagingResearchIndexFixtures(engine)
    assert resolver.resolve(FIXTURE) is None
    unavailable = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    try:
        broken = DatabaseStagingResearchIndexFixtures(unavailable)
        with pytest.raises(StagingResearchIndexFixtureControlUnavailable) as raised:
            broken.resolve(FIXTURE)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(broken) == "DatabaseStagingResearchIndexFixtures()"
        assert not hasattr(broken, "create") and not hasattr(broken, "change")
    finally:
        unavailable.dispose()
