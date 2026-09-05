import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.membership_authority_recovery import (
    main as membership_main,
)
from liquent_platform.operators.oidc_trust_authority_recovery import (
    main as oidc_main,
)
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)

pytestmark = pytest.mark.postgres_integration


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_both_recovery_operator_chains_run_on_postgresql(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path
) -> None:
    target = UserId("recovery-217-target")
    former = UserId("recovery-217-former")
    workspace = WorkspaceId("recovery-217-workspace")
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:target,'active'),(:former,'active')"
        ), {"target": target.encode(), "former": former.encode()})
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:target,'inactive'),(:former,'active')"
        ), {"target": target.encode(), "former": former.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:target,:workspace,'inactive'),(:former,:workspace,'active')"
        ), {
            "target": target.encode(), "former": former.encode(),
            "workspace": workspace.encode(),
        })
    oidc_expected = OidcTrustAuthoritySetRevisionId("recovery-217-oidc-expected")
    membership_expected = WorkspaceMembershipAuthoritySetRevisionId(
        "recovery-217-membership-expected"
    )
    assert DatabaseOidcTrustAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: oidc_expected
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("recovery-217-oidc-anchor"),
        SessionPrincipal(former),
    )
    assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: membership_expected
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "recovery-217-membership-anchor"
        ),
        SessionPrincipal(former), workspace,
    )
    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:former"),
            {"former": former.encode()},
        )
    database = _private(tmp_path / "database-url", postgres_url)
    oidc_request = _private(tmp_path / "oidc.json", json.dumps({
        "recovery_id": "recovery-217-oidc-id",
        "target_user_id": str(target),
        "expected_revision": oidc_expected.value,
    }))
    membership_request = _private(tmp_path / "membership.json", json.dumps({
        "recovery_id": "recovery-217-membership-id",
        "target_user_id": str(target),
        "workspace_id": str(workspace),
        "expected_revision": membership_expected.value,
    }))

    assert oidc_main([
        "recover", "--database-url-file", str(database), "--request",
        str(oidc_request), "--result-file", str(tmp_path / "oidc-result.json"),
    ]) == 0
    assert membership_main([
        "recover", "--database-url-file", str(database), "--request",
        str(membership_request), "--result-file",
        str(tmp_path / "membership-result.json"),
    ]) == 0
