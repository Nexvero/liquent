from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.ports import AuthorizedWorkspaceMembershipChangeStore
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipChangeConflict,
    WorkspaceMembershipChangeStoreUnavailable,
)
from liquent_platform.persistence.membership_changes import (
    DatabaseAuthorizedWorkspaceMembershipChanges,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.workspace_memberships import DatabaseWorkspaceMemberships

ACTOR = UserId("manager-209")
TARGET = UserId("member-209")
WORKSPACE = WorkspaceId("workspace-209")
CHANGE = WorkspaceMembershipChangeId("change-209")
REVISION_1 = WorkspaceMembershipRevisionId("revision-209-1")
REVISION_2 = WorkspaceMembershipRevisionId("revision-209-2")
PERMISSIONS = frozenset({Permission.RESEARCH_READ, Permission.RESEARCH_WRITE})


class Source:
    def __init__(self, *values: Any) -> None:
        self.values = list(values)
        self.calls = 0

    def __call__(self) -> Any:
        value = self.values[self.calls]
        self.calls += 1
        if isinstance(value, BaseException):
            raise value
        return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'changes.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine, *, authority: str = "active") -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:actor,'active'),(:target,'active')"
        ), {"actor": ACTOR.encode(), "target": TARGET.encode()})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": WORKSPACE.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities"
            " VALUES (:actor,:workspace,:status)"
        ), {
            "actor": ACTOR.encode(), "workspace": WORKSPACE.encode(),
            "status": authority,
        })


def _store(
    engine: Engine, source: Source
) -> DatabaseAuthorizedWorkspaceMembershipChanges:
    store: AuthorizedWorkspaceMembershipChangeStore = (
        DatabaseAuthorizedWorkspaceMembershipChanges(
            engine, generate_revision_id=source
        )
    )
    return store  # type: ignore[return-value]


def _create(engine: Engine, source: Source):
    return _store(engine, source).change_membership(
        CHANGE, SessionPrincipal(ACTOR), TARGET, WORKSPACE, None,
        MembershipStatus.ACTIVE, PERMISSIONS,
    )


def test_authorized_create_persists_full_snapshot_and_revision(engine: Engine) -> None:
    _foundation(engine)
    source = Source(REVISION_1)

    result = _create(engine, source)

    assert result is not None and result.revision_id == REVISION_1
    assert source.calls == 1
    membership = DatabaseWorkspaceMemberships(engine).get_membership(TARGET, WORKSPACE)
    assert membership is not None
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.permissions == PERMISSIONS
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT revision_id FROM workspace_memberships"
        )) == REVISION_1.value.encode()


def test_exact_retry_survives_authority_revocation_without_new_revision(
    engine: Engine,
) -> None:
    _foundation(engine)
    first = _create(engine, Source(REVISION_1))
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))
    source = Source(REVISION_2)

    repeated = _create(engine, source)

    assert repeated == first
    assert source.calls == 0


def test_same_change_with_different_snapshot_is_conflict(engine: Engine) -> None:
    _foundation(engine)
    store = _store(engine, Source(REVISION_1))
    assert store.change_membership(
        CHANGE, SessionPrincipal(ACTOR), TARGET, WORKSPACE, None,
        MembershipStatus.ACTIVE, PERMISSIONS,
    ) is not None

    with pytest.raises(WorkspaceMembershipChangeConflict):
        store.change_membership(
            CHANGE, SessionPrincipal(ACTOR), TARGET, WORKSPACE, None,
            MembershipStatus.ACTIVE, frozenset({Permission.RESEARCH_READ}),
        )


def test_update_requires_exact_current_revision(engine: Engine) -> None:
    _foundation(engine)
    source = Source(REVISION_1, REVISION_2)
    store = _store(engine, source)
    assert _create(engine, source) is not None

    rejected = store.change_membership(
        WorkspaceMembershipChangeId("stale"), SessionPrincipal(ACTOR), TARGET,
        WORKSPACE, WorkspaceMembershipRevisionId("other"),
        MembershipStatus.ACTIVE, frozenset({Permission.RESEARCH_READ}),
    )
    updated = store.change_membership(
        WorkspaceMembershipChangeId("update"), SessionPrincipal(ACTOR), TARGET,
        WORKSPACE, REVISION_1, MembershipStatus.ACTIVE,
        frozenset({Permission.RESEARCH_READ}),
    )

    assert rejected is None
    assert updated is not None and updated.revision_id == REVISION_2
    assert source.calls == 2


def test_deactivation_removes_current_permissions_but_preserves_history(
    engine: Engine,
) -> None:
    _foundation(engine)
    source = Source(REVISION_1, REVISION_2)
    assert _create(engine, source) is not None
    result = _store(engine, source).change_membership(
        WorkspaceMembershipChangeId("deactivate"), SessionPrincipal(ACTOR),
        TARGET, WORKSPACE, REVISION_1, MembershipStatus.INACTIVE, frozenset(),
    )

    assert result is not None and result.revision_id == REVISION_2
    membership = DatabaseWorkspaceMemberships(engine).get_membership(TARGET, WORKSPACE)
    assert membership is not None
    assert membership.status is MembershipStatus.INACTIVE
    assert membership.permissions == frozenset()
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revisions"
        )) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revision_permissions"
            " WHERE revision_id=:revision"
        ), {"revision": REVISION_1.value.encode()}) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revision_permissions"
            " WHERE revision_id=:revision"
        ), {"revision": REVISION_2.value.encode()}) == 0


def test_missing_authority_and_revisionsless_legacy_are_neutral(engine: Engine) -> None:
    _foundation(engine, authority="inactive")
    source = Source(REVISION_1)
    assert _create(engine, source) is None
    assert source.calls == 0
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities SET status='active'"
        ))
        connection.execute(text(
            "INSERT INTO workspace_memberships"
            " (user_id,workspace_id,status) VALUES (:target,:workspace,'active')"
        ), {"target": TARGET.encode(), "workspace": WORKSPACE.encode()})
    assert _store(engine, source).change_membership(
        WorkspaceMembershipChangeId("legacy"), SessionPrincipal(ACTOR), TARGET,
        WORKSPACE, REVISION_1, MembershipStatus.ACTIVE, frozenset(),
    ) is None
    assert source.calls == 0


def test_invalid_inactive_permissions_are_technical_and_write_nothing(
    engine: Engine,
) -> None:
    _foundation(engine)
    with pytest.raises(WorkspaceMembershipChangeStoreUnavailable):
        _store(engine, Source(REVISION_1)).change_membership(
            CHANGE, SessionPrincipal(ACTOR), TARGET, WORKSPACE, None,
            MembershipStatus.INACTIVE, frozenset({Permission.RESEARCH_READ}),
        )
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revisions"
        )) == 0


def test_generator_failure_rolls_back_everything(engine: Engine) -> None:
    _foundation(engine)
    with pytest.raises(WorkspaceMembershipChangeStoreUnavailable):
        _create(engine, Source(RuntimeError("secret")))
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_memberships"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM authorized_workspace_membership_changes"
        )) == 0


def test_unmigrated_store_is_detail_free(tmp_path: Path) -> None:
    database = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(database, Source(REVISION_1))
    try:
        with pytest.raises(WorkspaceMembershipChangeStoreUnavailable) as raised:
            store.change_membership(
                CHANGE, SessionPrincipal(ACTOR), TARGET, WORKSPACE, None,
                MembershipStatus.ACTIVE, PERMISSIONS,
            )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseAuthorizedWorkspaceMembershipChanges()"
    finally:
        database.dispose()
