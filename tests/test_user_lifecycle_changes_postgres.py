import threading
from datetime import UTC, datetime

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    UserLifecycleChangeId,
    UserLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.lifecycle_authority_sets import (
    DatabaseUserLifecycleAuthoritySets,
)
from liquent_platform.persistence.user_lifecycle_changes import (
    DatabaseAuthorizedUserLifecycleChanges,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_create_against_one_revision_has_one_success(
    postgres_url: str,
) -> None:
    setup = build_engine(postgres_url)
    material = SecureIdentityAuthorityMaterialGenerator()
    initial = UserLifecycleRevisionId("pg-user-initial")
    identity = DatabaseInitialIdentityAuthorityBootstrap(
        setup,
        generate_user_id=lambda: UserId("pg-user-actor"),
        generate_workspace_id=lambda: WorkspaceId("pg-user-workspace"),
        generate_user_revision_id=lambda: initial,
        generate_workspace_revision_id=material.new_workspace_lifecycle_revision_id,
    ).bootstrap()
    assert identity is not None
    assert DatabaseUserLifecycleAuthoritySets(
        setup,
        generate_revision_id=lambda: UserLifecycleAuthoritySetRevisionId(
            "pg-user-authority-anchor"
        ),
    ).anchor(
        UserLifecycleAuthorityChangeId("pg-user-authority-change"),
        SessionPrincipal(identity.user_id),
    ) is not None
    setup.dispose()

    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseAuthorizedUserLifecycleChanges(
                engine,
                generate_user_id=lambda: UserId(f"pg-created-{name}"),
                generate_revision_id=lambda: UserLifecycleRevisionId(
                    f"pg-created-revision-{name}"
                ),
                now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
            )
            start.wait(timeout=15)
            outcome: object = store.create_user(
                UserLifecycleChangeId(f"pg-create-{name}"),
                SessionPrincipal(identity.user_id),
                initial,
            )
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
