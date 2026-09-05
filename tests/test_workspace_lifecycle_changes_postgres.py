import threading

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.lifecycle_authority_sets import (
    DatabaseWorkspaceLifecycleAuthoritySets,
)
from liquent_platform.persistence.workspace_lifecycle_changes import (
    DatabaseAuthorizedWorkspaceLifecycleChanges,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_create_against_one_revision_has_one_success(
    postgres_url: str,
) -> None:
    setup = build_engine(postgres_url)
    material = SecureIdentityAuthorityMaterialGenerator()
    actor = UserId("pg-workspace-actor")
    initial = WorkspaceLifecycleRevisionId("pg-workspace-initial")
    identity = DatabaseInitialIdentityAuthorityBootstrap(
        setup,
        generate_user_id=lambda: actor,
        generate_workspace_id=lambda: WorkspaceId("pg-initial-workspace"),
        generate_user_revision_id=material.new_user_lifecycle_revision_id,
        generate_workspace_revision_id=lambda: initial,
    ).bootstrap()
    assert identity is not None
    assert DatabaseWorkspaceLifecycleAuthoritySets(
        setup,
        generate_revision_id=lambda: WorkspaceLifecycleAuthoritySetRevisionId(
            "pg-workspace-authority-anchor"
        ),
    ).anchor(
        WorkspaceLifecycleAuthorityChangeId("pg-workspace-authority-change"),
        SessionPrincipal(actor),
    ) is not None

    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseAuthorizedWorkspaceLifecycleChanges(
                engine,
                generate_workspace_id=lambda: WorkspaceId(f"pg-workspace-{name}"),
                generate_revision_id=lambda: WorkspaceLifecycleRevisionId(
                    f"pg-workspace-revision-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.create_workspace(
                WorkspaceLifecycleChangeId(f"pg-workspace-change-{name}"),
                SessionPrincipal(actor), actor, initial,
            )
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    setup.dispose()
    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
