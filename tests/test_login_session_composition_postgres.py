from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.login_session_composition import (
    compose_login_sessions,
)

pytestmark = pytest.mark.postgres_integration
NOW = datetime(2026, 8, 12, tzinfo=UTC)


def test_composed_transaction_and_session_lifecycle(postgres_engine: Engine) -> None:
    user = UserId("user-191")
    assert DatabaseInitialIdentityAuthorityBootstrap(
        postgres_engine,
        generate_user_id=lambda: user,
        generate_workspace_id=lambda: WorkspaceId("workspace-191"),
        generate_user_revision_id=lambda: UserLifecycleRevisionId(
            "user-revision-191"
        ),
        generate_workspace_revision_id=lambda: WorkspaceLifecycleRevisionId(
            "workspace-revision-191"
        ),
    ).bootstrap() is not None
    composition = compose_login_sessions(
        postgres_engine,
        session_lifetime=timedelta(hours=1),
        now=lambda: NOW,
    )
    state = OidcLoginState("state-191")
    pending = PendingOidcLoginTransaction(
        expected_issuer="https://idp.example",
        expected_nonce="nonce",
        code_verifier="verifier",
        redirect_uri="https://app.example/callback",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    assert composition.transactions.add_transaction(state, pending) is True
    assert composition.transactions.claim_transaction(state) == pending

    issued = composition.issue_session(SessionPrincipal(user))
    assert composition.sessions.get_session(issued.session_id) is not None
    replacement = composition.rotate_session(issued.session_id)
    assert composition.sessions.get_session(issued.session_id) is None
    assert composition.sessions.get_session(replacement.session_id) is not None
    composition.sessions.revoke_session(replacement.session_id)
    assert composition.sessions.get_session(replacement.session_id) is None
