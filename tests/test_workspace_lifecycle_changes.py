from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    AuthorizedWorkspaceLifecycleChange,
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleIntent,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.ports import AuthorizedWorkspaceLifecycleStore
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.identity_errors import (
    WorkspaceLifecycleChangeConflict,
)
from liquent_platform.persistence.lifecycle_authority_sets import (
    DatabaseWorkspaceLifecycleAuthoritySets,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.workspace_lifecycle_changes import (
    DatabaseAuthorizedWorkspaceLifecycleChanges,
)

ACTOR = UserId("workspace-lifecycle-actor")
MANAGER = UserId("workspace-onboarding-manager")
INITIAL = WorkspaceId("initial-workspace")
INITIAL_REVISION = WorkspaceLifecycleRevisionId("initial-workspace-revision")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'workspaces.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine, *, manager_active: bool = True) -> None:
    material = SecureIdentityAuthorityMaterialGenerator()
    identity = DatabaseInitialIdentityAuthorityBootstrap(
        engine,
        generate_user_id=lambda: ACTOR,
        generate_workspace_id=lambda: INITIAL,
        generate_user_revision_id=material.new_user_lifecycle_revision_id,
        generate_workspace_revision_id=lambda: INITIAL_REVISION,
    ).bootstrap()
    assert identity is not None
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:manager,:status)"),
            {
                "manager": MANAGER.encode(),
                "status": "active" if manager_active else "inactive",
            },
        )
    assert DatabaseWorkspaceLifecycleAuthoritySets(
        engine,
        generate_revision_id=lambda: WorkspaceLifecycleAuthoritySetRevisionId(
            "workspace-authority-anchor"
        ),
    ).anchor(
        WorkspaceLifecycleAuthorityChangeId("workspace-authority-change"),
        SessionPrincipal(ACTOR),
    ) is not None


def _store(
    engine: Engine,
    workspaces: list[WorkspaceId],
    revisions: list[WorkspaceLifecycleRevisionId],
) -> DatabaseAuthorizedWorkspaceLifecycleChanges:
    return DatabaseAuthorizedWorkspaceLifecycleChanges(
        engine,
        generate_workspace_id=lambda: workspaces.pop(0),
        generate_revision_id=lambda: revisions.pop(0),
    )


def test_create_and_terminal_deactivate_form_complete_revisions(
    engine: Engine,
) -> None:
    _foundation(engine)
    created_workspace = WorkspaceId("created-workspace")
    port: AuthorizedWorkspaceLifecycleStore = _store(
        engine,
        [created_workspace],
        [
            WorkspaceLifecycleRevisionId("after-create"),
            WorkspaceLifecycleRevisionId("after-deactivate"),
        ],
    )
    created = port.create_workspace(
        WorkspaceLifecycleChangeId("create-workspace"),
        SessionPrincipal(ACTOR),
        MANAGER,
        INITIAL_REVISION,
    )
    assert created == AuthorizedWorkspaceLifecycleChange(
        WorkspaceLifecycleChangeId("create-workspace"),
        WorkspaceLifecycleRevisionId("after-create"),
        created_workspace,
        MANAGER,
        WorkspaceLifecycleIntent.CREATE,
    )
    deactivated = port.deactivate_workspace(
        WorkspaceLifecycleChangeId("deactivate-workspace"),
        SessionPrincipal(ACTOR),
        created_workspace,
        WorkspaceLifecycleRevisionId("after-create"),
    )
    assert deactivated is not None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM identity_workspaces WHERE workspace_id=:workspace"
        ), {"workspace": created_workspace.encode()}) == "inactive"
        assert connection.execute(text(
            "SELECT user_id,status FROM workspace_onboarding_management"
            " WHERE workspace_id=:workspace"
        ), {"workspace": created_workspace.encode()}).one() == (
            MANAGER.encode(), "active"
        )
        assert connection.execute(text(
            "SELECT workspace_id,status FROM workspace_lifecycle_revision_members"
            " WHERE revision_id=:revision ORDER BY workspace_id"
        ), {"revision": b"after-deactivate"}).all() == [
            (created_workspace.encode(), "inactive"),
            (INITIAL.encode(), "active"),
        ]


def test_create_rejects_inactive_first_manager_without_drawing(engine: Engine) -> None:
    _foundation(engine, manager_active=False)
    workspaces = [WorkspaceId("unused")]
    revisions = [WorkspaceLifecycleRevisionId("unused")]
    store = _store(engine, workspaces, revisions)
    assert store.create_workspace(
        WorkspaceLifecycleChangeId("inactive-manager"),
        SessionPrincipal(ACTOR),
        MANAGER,
        INITIAL_REVISION,
    ) is None
    assert len(workspaces) == len(revisions) == 1


def test_stale_revision_and_second_deactivate_are_neutral(engine: Engine) -> None:
    _foundation(engine)
    store = _store(
        engine,
        [WorkspaceId("unused")],
        [WorkspaceLifecycleRevisionId("deactivated")],
    )
    assert store.create_workspace(
        WorkspaceLifecycleChangeId("stale"), SessionPrincipal(ACTOR), MANAGER,
        WorkspaceLifecycleRevisionId("stale"),
    ) is None
    result = store.deactivate_workspace(
        WorkspaceLifecycleChangeId("deactivate-initial"),
        SessionPrincipal(ACTOR), INITIAL, INITIAL_REVISION,
    )
    assert result is not None
    assert store.deactivate_workspace(
        WorkspaceLifecycleChangeId("deactivate-again"),
        SessionPrincipal(ACTOR), INITIAL,
        WorkspaceLifecycleRevisionId("deactivated"),
    ) is None


def test_exact_create_retry_survives_authority_revocation(engine: Engine) -> None:
    _foundation(engine)
    store = _store(
        engine,
        [WorkspaceId("retry-workspace")],
        [WorkspaceLifecycleRevisionId("retry-revision")],
    )
    change = WorkspaceLifecycleChangeId("retry-change")
    expected = store.create_workspace(
        change, SessionPrincipal(ACTOR), MANAGER, INITIAL_REVISION
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_lifecycle_management_authorities"
            " SET status='inactive'"
        ))
    assert store.create_workspace(
        change, SessionPrincipal(ACTOR), MANAGER, INITIAL_REVISION
    ) == expected
    with pytest.raises(WorkspaceLifecycleChangeConflict):
        store.deactivate_workspace(
            change, SessionPrincipal(ACTOR), WorkspaceId("retry-workspace"),
            INITIAL_REVISION,
        )


def test_create_adds_no_membership_or_other_authority(engine: Engine) -> None:
    _foundation(engine)
    store = _store(
        engine,
        [WorkspaceId("isolated-workspace")],
        [WorkspaceLifecycleRevisionId("isolated-revision")],
    )
    assert store.create_workspace(
        WorkspaceLifecycleChangeId("isolated-create"),
        SessionPrincipal(ACTOR), MANAGER, INITIAL_REVISION,
    ) is not None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_memberships"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_management_authorities"
        )) == 0
