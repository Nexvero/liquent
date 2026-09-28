from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    LifecycleAuthorityIntent,
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import bootstrap_identity
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    LifecycleAuthoritySetConflict,
)
from liquent_platform.persistence.lifecycle_authority_sets import (
    DatabaseUserLifecycleAuthoritySets,
    DatabaseWorkspaceLifecycleAuthoritySets,
)
from liquent_platform.persistence.migrate import upgrade_to_head

ACTOR = UserId("authority-actor-222")
TARGET = UserId("authority-target-222")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'authority-sets.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine) -> None:
    with engine.begin() as connection:
        for user in (ACTOR, TARGET):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )


@pytest.mark.parametrize("domain", ["user", "workspace"])
def test_anchor_and_full_regular_lifecycle(engine: Engine, domain: str) -> None:
    _foundation(engine)
    authority = (
        "user_lifecycle_management_authorities"
        if domain == "user"
        else "workspace_lifecycle_management_authorities"
    )
    with engine.begin() as connection:
        connection.execute(text(
            f"INSERT INTO {authority} VALUES (:actor,'active')"
        ), {"actor": ACTOR.encode()})

    if domain == "user":
        revisions = iter(UserLifecycleAuthoritySetRevisionId(value) for value in (
            "user-anchor", "user-grant", "user-deactivate", "user-reactivate"
        ))
        store = DatabaseUserLifecycleAuthoritySets(
            engine, generate_revision_id=lambda: next(revisions)
        )
        change = UserLifecycleAuthorityChangeId
    else:
        revisions = iter(WorkspaceLifecycleAuthoritySetRevisionId(value) for value in (
            "workspace-anchor", "workspace-grant", "workspace-deactivate",
            "workspace-reactivate",
        ))
        store = DatabaseWorkspaceLifecycleAuthoritySets(
            engine, generate_revision_id=lambda: next(revisions)
        )
        change = WorkspaceLifecycleAuthorityChangeId

    anchored = store.anchor(change(f"{domain}-anchor-change"), SessionPrincipal(ACTOR))
    assert anchored is not None
    expected = anchored.revision_id
    grant = store.change_authority(
        change(f"{domain}-grant-change"), SessionPrincipal(ACTOR), TARGET,
        LifecycleAuthorityIntent.GRANT, expected,
    )
    assert grant is not None
    deactivate = store.change_authority(
        change(f"{domain}-deactivate-change"), SessionPrincipal(ACTOR), ACTOR,
        LifecycleAuthorityIntent.DEACTIVATE, grant.revision_id,
    )
    assert deactivate is not None
    reactivate = store.change_authority(
        change(f"{domain}-reactivate-change"), SessionPrincipal(TARGET), ACTOR,
        LifecycleAuthorityIntent.REACTIVATE, deactivate.revision_id,
    )
    assert reactivate is not None

    prefix = f"{domain}_lifecycle"
    with engine.connect() as connection:
        assert connection.execute(text(
            f"SELECT user_id,status FROM {authority} ORDER BY user_id"
        )).all() == [(ACTOR.encode(), "active"), (TARGET.encode(), "active")]
        assert connection.scalar(text(
            f"SELECT count(*) FROM {prefix}_authority_set_revisions"
        )) == 4
        assert connection.scalar(text(
            f"SELECT count(*) FROM {prefix}_authority_changes"
        )) == 4


@pytest.mark.parametrize("domain", ["user", "workspace"])
def test_last_effective_manager_and_stale_revision_are_neutral(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    authority = f"{domain}_lifecycle_management_authorities"
    with engine.begin() as connection:
        connection.execute(text(
            f"INSERT INTO {authority} VALUES (:actor,'active')"
        ), {"actor": ACTOR.encode()})
    if domain == "user":
        store = DatabaseUserLifecycleAuthoritySets(
            engine,
            generate_revision_id=lambda: UserLifecycleAuthoritySetRevisionId("anchor"),
        )
        change = UserLifecycleAuthorityChangeId
        stale = UserLifecycleAuthoritySetRevisionId("stale")
    else:
        store = DatabaseWorkspaceLifecycleAuthoritySets(
            engine,
            generate_revision_id=lambda: WorkspaceLifecycleAuthoritySetRevisionId(
                "anchor"
            ),
        )
        change = WorkspaceLifecycleAuthorityChangeId
        stale = WorkspaceLifecycleAuthoritySetRevisionId("stale")
    anchored = store.anchor(change("anchor-change"), SessionPrincipal(ACTOR))
    assert anchored is not None
    assert store.change_authority(
        change("last-manager"), SessionPrincipal(ACTOR), ACTOR,
        LifecycleAuthorityIntent.DEACTIVATE, anchored.revision_id,
    ) is None
    assert store.change_authority(
        change("stale-change"), SessionPrincipal(ACTOR), TARGET,
        LifecycleAuthorityIntent.GRANT, stale,
    ) is None


def test_exact_retry_survives_revocation_and_changed_reuse_conflicts(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO user_lifecycle_management_authorities"
            " VALUES (:actor,'active')"
        ), {"actor": ACTOR.encode()})
    revisions = iter(UserLifecycleAuthoritySetRevisionId(value) for value in (
        "anchor-revision", "grant-revision"
    ))
    store = DatabaseUserLifecycleAuthoritySets(
        engine, generate_revision_id=lambda: next(revisions)
    )
    anchor = store.anchor(
        UserLifecycleAuthorityChangeId("anchor"), SessionPrincipal(ACTOR)
    )
    assert anchor is not None
    change = UserLifecycleAuthorityChangeId("grant")
    result = store.change_authority(
        change, SessionPrincipal(ACTOR), TARGET,
        LifecycleAuthorityIntent.GRANT, anchor.revision_id,
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE user_lifecycle_management_authorities SET status='inactive'"
        ))
    assert store.change_authority(
        change, SessionPrincipal(ACTOR), TARGET,
        LifecycleAuthorityIntent.GRANT, anchor.revision_id,
    ) == result
    with pytest.raises(LifecycleAuthoritySetConflict):
        store.change_authority(
            change, SessionPrincipal(ACTOR), ACTOR,
            LifecycleAuthorityIntent.GRANT, anchor.revision_id,
        )


def test_new_foundations_are_empty(engine: Engine) -> None:
    tables = (
        "user_lifecycle_authority_set_revisions",
        "user_lifecycle_authority_set_members",
        "user_lifecycle_authority_current_set",
        "user_lifecycle_authority_changes",
        "workspace_lifecycle_authority_set_revisions",
        "workspace_lifecycle_authority_set_members",
        "workspace_lifecycle_authority_current_set",
        "workspace_lifecycle_authority_changes",
    )
    with engine.connect() as connection:
        assert all(connection.scalar(text(
            f"SELECT count(*) FROM {table}"
        )) == 0 for table in tables)


def test_secure_material_draws_four_separate_authority_ids(monkeypatch) -> None:
    values = iter(f"authority-222-{index}" for index in range(4))
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()
    generated = (
        material.new_user_lifecycle_authority_set_revision_id(),
        material.new_user_lifecycle_authority_change_id(),
        material.new_workspace_lifecycle_authority_set_revision_id(),
        material.new_workspace_lifecycle_authority_change_id(),
    )
    assert tuple(item.value for item in generated) == tuple(
        f"authority-222-{index}" for index in range(4)
    )


def test_authority_anchor_closes_initial_bootstrap_recovery(engine: Engine) -> None:
    material = SecureIdentityAuthorityMaterialGenerator()
    identity = bootstrap_identity(engine, material)
    assert identity is not None
    store = DatabaseUserLifecycleAuthoritySets(
        engine,
        generate_revision_id=lambda: UserLifecycleAuthoritySetRevisionId(
            "recovery-closing-anchor"
        ),
    )
    assert store.anchor(
        UserLifecycleAuthorityChangeId("recovery-closing-change"),
        SessionPrincipal(identity.result.user_id),
    ) is not None
    assert bootstrap_identity(engine, material) is None
