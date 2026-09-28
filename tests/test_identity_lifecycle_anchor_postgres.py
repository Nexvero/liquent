import threading

import pytest
from sqlalchemy import text

from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_lifecycle_anchor import (
    DatabaseInitialIdentityLifecycleFoundationAnchor,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_anchor_has_exactly_one_success(postgres_url: str) -> None:
    setup = build_engine(postgres_url)
    with setup.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES (:user,'active')"
        ), {"user": b"u"})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": b"w"})
        connection.execute(text(
            "INSERT INTO workspace_onboarding_management"
            " VALUES (:user,:workspace,'active')"
        ), {"user": b"u", "workspace": b"w"})
    setup.dispose()

    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseInitialIdentityLifecycleFoundationAnchor(
                engine,
                generate_user_revision_id=lambda: UserLifecycleRevisionId(
                    f"user-anchor-{name}"
                ),
                generate_workspace_revision_id=lambda: WorkspaceLifecycleRevisionId(
                    f"workspace-anchor-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.anchor()
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
