from pathlib import Path

from sqlalchemy import Engine, text

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityLifecycleIntent,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.membership_authority_lifecycle import (
    DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle,
)
from liquent_platform.persistence.membership_management_bootstrap import (
    DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_lifecycle import (
    DatabaseAuthorizedOidcTrustAuthorityLifecycle,
)
from liquent_platform.persistence.oidc_trust_bootstrap import (
    DatabaseInitialOidcTrustAuthorityBootstrap,
)


def _engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'lq218.db'}"
    upgrade_to_head(url)
    return build_engine(url)


def test_supported_empty_store_chain_reaches_both_anchored_first_managers(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    material = SecureIdentityAuthorityMaterialGenerator()
    try:
        identity = DatabaseInitialIdentityAuthorityBootstrap(
            engine,
            generate_user_id=material.new_user_id,
            generate_workspace_id=material.new_workspace_id,
            generate_user_revision_id=material.new_user_lifecycle_revision_id,
            generate_workspace_revision_id=material.new_workspace_lifecycle_revision_id,
        ).bootstrap()
        assert identity is not None
        assert DatabaseInitialOidcTrustAuthorityBootstrap(engine).bootstrap(
            identity.user_id
        ) is not None
        assert DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(
            engine
        ).bootstrap(identity.user_id, identity.workspace_id) is not None

        principal = SessionPrincipal(identity.user_id)
        global_revision = OidcTrustAuthoritySetRevisionId(
            "lq218-global-anchor-revision"
        )
        workspace_revision = WorkspaceMembershipAuthoritySetRevisionId(
            "lq218-workspace-anchor-revision"
        )
        assert DatabaseOidcTrustAuthoritySetAnchor(
            engine, generate_revision_id=lambda: global_revision
        ).anchor(
            OidcTrustAuthorityLifecycleChangeId("lq218-global-anchor"),
            principal,
        ) is not None
        assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
            engine, generate_revision_id=lambda: workspace_revision
        ).anchor(
            WorkspaceMembershipAuthorityLifecycleChangeId(
                "lq218-workspace-anchor"
            ),
            principal,
            identity.workspace_id,
        ) is not None

        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM identity_users")) == 1
            assert connection.scalar(
                text("SELECT count(*) FROM identity_workspaces")
            ) == 1
            assert connection.scalar(text(
                "SELECT count(*) FROM oidc_trust_authority_current_set"
            )) == 1
            assert connection.scalar(text(
                "SELECT count(*) FROM workspace_membership_authority_current_sets"
            )) == 1
    finally:
        engine.dispose()


def test_sole_bootstrap_manager_cannot_be_rotated_or_made_recoverable(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    material = SecureIdentityAuthorityMaterialGenerator()
    try:
        identity = DatabaseInitialIdentityAuthorityBootstrap(
            engine,
            generate_user_id=material.new_user_id,
            generate_workspace_id=material.new_workspace_id,
            generate_user_revision_id=material.new_user_lifecycle_revision_id,
            generate_workspace_revision_id=material.new_workspace_lifecycle_revision_id,
        ).bootstrap()
        assert identity is not None
        DatabaseInitialOidcTrustAuthorityBootstrap(engine).bootstrap(identity.user_id)
        DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(
            engine
        ).bootstrap(identity.user_id, identity.workspace_id)
        principal = SessionPrincipal(identity.user_id)
        global_revision = OidcTrustAuthoritySetRevisionId(
            "lq218-single-global-anchor"
        )
        workspace_revision = WorkspaceMembershipAuthoritySetRevisionId(
            "lq218-single-workspace-anchor"
        )
        DatabaseOidcTrustAuthoritySetAnchor(
            engine, generate_revision_id=lambda: global_revision
        ).anchor(
            OidcTrustAuthorityLifecycleChangeId("lq218-single-global-change"),
            principal,
        )
        DatabaseWorkspaceMembershipAuthoritySetAnchor(
            engine, generate_revision_id=lambda: workspace_revision
        ).anchor(
            WorkspaceMembershipAuthorityLifecycleChangeId(
                "lq218-single-workspace-change"
            ),
            principal,
            identity.workspace_id,
        )

        assert DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "must-not-be-drawn"
            ),
        ).change_authority(
            OidcTrustAuthorityLifecycleChangeId("lq218-global-deactivate"),
            principal,
            identity.user_id,
            OidcTrustAuthorityLifecycleIntent.DEACTIVATE,
            global_revision,
        ) is None
        assert DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("must-not-be-drawn")
            ),
        ).change_authority(
            WorkspaceMembershipAuthorityLifecycleChangeId(
                "lq218-workspace-deactivate"
            ),
            principal,
            identity.user_id,
            identity.workspace_id,
            WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE,
            workspace_revision,
        ) is None

        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM identity_users")) == 1
            assert connection.scalar(text(
                "SELECT count(*) FROM oidc_trust_authority_recoveries"
            )) == 0
            assert connection.scalar(text(
                "SELECT count(*) FROM workspace_membership_authority_recoveries"
            )) == 0
    finally:
        engine.dispose()


def test_runtime_process_contains_no_control_plane_or_recovery_import() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "src/liquent_platform/transport/http/main.py").read_text(
        encoding="utf-8"
    )
    app = (root / "src/liquent_platform/transport/http/app.py").read_text(
        encoding="utf-8"
    )

    for token in (
        "identity_bootstrap",
        "membership_management_bootstrap",
        "oidc_trust_bootstrap",
        "authority_anchor",
        "authority_lifecycle",
        "authority_recovery",
        "operators.",
    ):
        assert token not in runtime
        assert token not in app


def test_later_lifecycle_control_plane_remains_outside_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    ports = (root / "src/liquent_platform/identity/ports.py").read_text(
        encoding="utf-8"
    )
    runtime = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "src/liquent_platform/transport/http/main.py",
            "src/liquent_platform/transport/http/app.py",
        )
    )

    assert "AuthorizedUserLifecycleStore" in ports
    assert "AuthorizedWorkspaceLifecycleStore" in ports
    assert "operators.user_lifecycle" not in runtime
    assert "operators.workspace_lifecycle" not in runtime
