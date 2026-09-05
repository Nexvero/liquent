from __future__ import annotations

import threading

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_bootstrap_has_exactly_one_winner(postgres_url: str) -> None:
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseInitialIdentityAuthorityBootstrap(
                engine,
                generate_user_id=lambda: UserId(f"user-{name}"),
                generate_workspace_id=lambda: WorkspaceId(f"workspace-{name}"),
                generate_user_revision_id=lambda: UserLifecycleRevisionId(
                    f"user-revision-{name}"
                ),
                generate_workspace_revision_id=lambda: WorkspaceLifecycleRevisionId(
                    f"workspace-revision-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.bootstrap()
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

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert len(outcomes) == 2
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
