from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    AuthorizedUserLifecycleChange,
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    UserLifecycleChangeId,
    UserLifecycleIntent,
    UserLifecycleRevisionId,
)
from liquent_platform.identity.ports import AuthorizedUserLifecycleStore
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.identity_errors import UserLifecycleChangeConflict
from liquent_platform.persistence.lifecycle_authority_sets import (
    DatabaseUserLifecycleAuthoritySets,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.user_lifecycle_changes import (
    DatabaseAuthorizedUserLifecycleChanges,
)

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
ACTOR = UserId("user-lifecycle-actor")
WORKSPACE = "user-lifecycle-workspace"
INITIAL_REVISION = UserLifecycleRevisionId("initial-user-revision")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'users.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine) -> None:
    material = SecureIdentityAuthorityMaterialGenerator()
    identity = DatabaseInitialIdentityAuthorityBootstrap(
        engine,
        generate_user_id=lambda: ACTOR,
        generate_workspace_id=lambda: WORKSPACE,
        generate_user_revision_id=lambda: INITIAL_REVISION,
        generate_workspace_revision_id=material.new_workspace_lifecycle_revision_id,
    ).bootstrap()
    assert identity is not None
    anchored = DatabaseUserLifecycleAuthoritySets(
        engine,
        generate_revision_id=lambda: UserLifecycleAuthoritySetRevisionId(
            "user-authority-anchor"
        ),
    ).anchor(
        UserLifecycleAuthorityChangeId("user-authority-anchor-change"),
        SessionPrincipal(ACTOR),
    )
    assert anchored is not None


def _store(
    engine: Engine,
    users: list[UserId],
    revisions: list[UserLifecycleRevisionId],
) -> DatabaseAuthorizedUserLifecycleChanges:
    return DatabaseAuthorizedUserLifecycleChanges(
        engine,
        generate_user_id=lambda: users.pop(0),
        generate_revision_id=lambda: revisions.pop(0),
        now=lambda: NOW,
    )


def test_create_deactivate_and_reactivate_form_complete_revisions(
    engine: Engine,
) -> None:
    _foundation(engine)
    target = UserId("created-user")
    store: AuthorizedUserLifecycleStore = _store(
        engine,
        [target],
        [
            UserLifecycleRevisionId("after-create"),
            UserLifecycleRevisionId("after-deactivate"),
            UserLifecycleRevisionId("after-reactivate"),
        ],
    )
    created = store.create_user(
        UserLifecycleChangeId("create-change"),
        SessionPrincipal(ACTOR),
        INITIAL_REVISION,
    )
    assert created == AuthorizedUserLifecycleChange(
        UserLifecycleChangeId("create-change"),
        UserLifecycleRevisionId("after-create"),
        target,
        UserLifecycleIntent.CREATE,
    )
    deactivated = store.change_user_status(
        UserLifecycleChangeId("deactivate-change"),
        SessionPrincipal(ACTOR),
        target,
        UserLifecycleIntent.DEACTIVATE,
        UserLifecycleRevisionId("after-create"),
    )
    assert deactivated is not None
    reactivated = store.change_user_status(
        UserLifecycleChangeId("reactivate-change"),
        SessionPrincipal(ACTOR),
        target,
        UserLifecycleIntent.REACTIVATE,
        UserLifecycleRevisionId("after-deactivate"),
    )
    assert reactivated is not None
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM identity_users ORDER BY user_id"
        )).all() == [(target.encode(), "active"), (ACTOR.encode(), "active")]
        assert connection.execute(text(
            "SELECT user_id,status FROM user_lifecycle_revision_members"
            " WHERE revision_id=:revision ORDER BY user_id"
        ), {"revision": b"after-deactivate"}).all() == [
            (target.encode(), "inactive"), (ACTOR.encode(), "active")
        ]


@pytest.mark.parametrize(
    "dependency",
    [
        "session", "admission", "membership", "onboarding",
        "membership-authority", "trust-authority", "user-authority",
        "workspace-authority",
    ],
)
def test_deactivate_requires_complete_drain(
    engine: Engine, dependency: str
) -> None:
    _foundation(engine)
    target = UserId("drain-target")
    store = _store(
        engine, [target],
        [UserLifecycleRevisionId("created"), UserLifecycleRevisionId("unused")],
    )
    created = store.create_user(
        UserLifecycleChangeId("create"), SessionPrincipal(ACTOR), INITIAL_REVISION
    )
    assert created is not None
    with engine.begin() as connection:
        if dependency == "session":
            connection.execute(text(
                "INSERT INTO browser_sessions VALUES"
                " (:id,:user,:csrf,:expires,NULL)"
            ), {"id": b"session", "user": target.encode(), "csrf": b"csrf",
                "expires": NOW + timedelta(hours=1)})
        elif dependency == "admission":
            connection.execute(text(
                "INSERT INTO identity_admissions VALUES"
                " (:id,:request,:user,:workspace,1,:expires,NULL,NULL,NULL)"
            ), {"id": b"admission", "request": b"request",
                "user": target.encode(), "workspace": WORKSPACE.encode(),
                "expires": NOW + timedelta(hours=1)})
        elif dependency == "membership":
            connection.execute(text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status,revision_id)"
                " VALUES (:user,:workspace,'active',NULL)"
            ), {"user": target.encode(), "workspace": WORKSPACE.encode()})
        else:
            table = {
                "onboarding": "workspace_onboarding_management",
                "membership-authority": (
                    "workspace_membership_management_authorities"
                ),
                "trust-authority": "oidc_trust_management_authorities",
                "user-authority": "user_lifecycle_management_authorities",
                "workspace-authority": (
                    "workspace_lifecycle_management_authorities"
                ),
            }[dependency]
            if dependency in {"onboarding", "membership-authority"}:
                connection.execute(text(
                    f"INSERT INTO {table} VALUES (:user,:workspace,'active')"
                ), {"user": target.encode(), "workspace": WORKSPACE.encode()})
            else:
                connection.execute(text(
                    f"INSERT INTO {table} VALUES (:user,'active')"
                ), {"user": target.encode()})
    assert store.change_user_status(
        UserLifecycleChangeId(f"deactivate-{dependency}"),
        SessionPrincipal(ACTOR), target, UserLifecycleIntent.DEACTIVATE,
        UserLifecycleRevisionId("created"),
    ) is None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM identity_users WHERE user_id=:user"
        ), {"user": target.encode()}) == "active"


def test_exact_create_retry_returns_generated_target_after_revocation(
    engine: Engine,
) -> None:
    _foundation(engine)
    target = UserId("retry-target")
    store = _store(
        engine, [target], [UserLifecycleRevisionId("retry-revision")]
    )
    change = UserLifecycleChangeId("retry-create")
    expected = store.create_user(change, SessionPrincipal(ACTOR), INITIAL_REVISION)
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE user_lifecycle_management_authorities SET status='inactive'"
        ))
    assert store.create_user(
        change, SessionPrincipal(ACTOR), INITIAL_REVISION
    ) == expected
    with pytest.raises(UserLifecycleChangeConflict):
        store.change_user_status(
            change, SessionPrincipal(ACTOR), target,
            UserLifecycleIntent.DEACTIVATE, INITIAL_REVISION,
        )


def test_stale_revision_and_inactive_actor_are_neutral(engine: Engine) -> None:
    _foundation(engine)
    store = _store(
        engine, [UserId("unused")], [UserLifecycleRevisionId("unused")]
    )
    assert store.create_user(
        UserLifecycleChangeId("stale"), SessionPrincipal(ACTOR),
        UserLifecycleRevisionId("stale"),
    ) is None
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE identity_users SET status='inactive' WHERE user_id=:actor"
        ), {"actor": ACTOR.encode()})
    assert store.create_user(
        UserLifecycleChangeId("inactive"), SessionPrincipal(ACTOR), INITIAL_REVISION
    ) is None


def test_migration_indexes_unkeyed_drain_lookups(engine: Engine) -> None:
    assert {item["name"] for item in inspect(engine).get_indexes(
        "browser_sessions"
    )} >= {"ix_browser_sessions_user"}
    assert {item["name"] for item in inspect(engine).get_indexes(
        "identity_admissions"
    )} >= {"ix_identity_admissions_target_user"}
