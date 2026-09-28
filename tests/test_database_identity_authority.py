from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_authority import (
    DatabaseOnboardingManagementAuthority,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head

ACTOR = UserId("actor-1")
TARGET = UserId("target-1")
WORKSPACE = WorkspaceId("workspace-1")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'authority.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _facts(
    engine: Engine,
    *,
    actor_status: str = "active",
    target_status: str = "active",
    workspace_status: str = "active",
    authority_status: str | None = "active",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users (user_id, status) VALUES (:id, :status)"),
            {"id": str(ACTOR).encode(), "status": actor_status},
        )
        connection.execute(
            text("INSERT INTO identity_users (user_id, status) VALUES (:id, :status)"),
            {"id": str(TARGET).encode(), "status": target_status},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id, status)"
                " VALUES (:id, :status)"
            ),
            {"id": str(WORKSPACE).encode(), "status": workspace_status},
        )
        if authority_status is not None:
            connection.execute(
                text(
                    "INSERT INTO workspace_onboarding_management"
                    " (user_id, workspace_id, status)"
                    " VALUES (:user, :workspace, :status)"
                ),
                {
                    "user": str(ACTOR).encode(),
                    "workspace": str(WORKSPACE).encode(),
                    "status": authority_status,
                },
            )


def _decision(engine: Engine) -> bool:
    return DatabaseOnboardingManagementAuthority(
        engine
    ).permits_onboarding_management(
        SessionPrincipal(ACTOR), TARGET, WORKSPACE
    )


def test_all_active_persistent_facts_permit(engine: Engine) -> None:
    _facts(engine)

    assert _decision(engine) is True


@pytest.mark.parametrize(
    "change",
    ["actor", "target", "workspace", "authority", "absent-authority"],
)
def test_absence_or_inactivity_fails_closed(engine: Engine, change: str) -> None:
    _facts(
        engine,
        actor_status="inactive" if change == "actor" else "active",
        target_status="inactive" if change == "target" else "active",
        workspace_status="inactive" if change == "workspace" else "active",
        authority_status=(
            None
            if change == "absent-authority"
            else "inactive" if change == "authority" else "active"
        ),
    )

    assert _decision(engine) is False


def test_revocation_affects_the_next_decision(engine: Engine) -> None:
    _facts(engine)
    assert _decision(engine) is True

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE workspace_onboarding_management SET status='inactive'"
                " WHERE user_id=:user AND workspace_id=:workspace"
            ),
            {"user": str(ACTOR).encode(), "workspace": str(WORKSPACE).encode()},
        )

    assert _decision(engine) is False


def test_wrong_workspace_never_inherits_authority(engine: Engine) -> None:
    _facts(engine)

    assert DatabaseOnboardingManagementAuthority(
        engine
    ).permits_onboarding_management(
        SessionPrincipal(ACTOR), TARGET, WorkspaceId("workspace-2")
    ) is False


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = DatabaseOnboardingManagementAuthority(engine)
    try:
        with pytest.raises(IdentityAuthorityStoreUnavailable) as raised:
            store.permits_onboarding_management(
                SessionPrincipal(ACTOR), TARGET, WORKSPACE
            )
        assert raised.value.args == ("identity_authority_store_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseOnboardingManagementAuthority()"
    finally:
        engine.dispose()
