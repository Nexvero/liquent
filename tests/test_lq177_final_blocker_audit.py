from pathlib import Path

import liquent_platform.transport.http.main as runtime
from liquent_platform.configuration import PlatformSettings
from liquent_platform.persistence.oidc_client_configuration import (
    DatabaseActiveOidcClientConfiguration,
)
from liquent_platform.persistence.workspace_memberships import (
    DatabaseWorkspaceMemberships,
)
from liquent_platform.transport.http.app import create_app


def test_real_process_entrypoint_keeps_oidc_closed_without_runtime_dependencies(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def record(settings, **dependencies):
        captured.update(dependencies)
        return sentinel

    monkeypatch.setattr(runtime, "create_app", record)
    result = runtime.build_app(PlatformSettings(_secrets_dir=None))

    assert result is sentinel
    assert set(captured) == {"research_resolver"}
    assert captured["research_resolver"] is None


def test_runtime_settings_now_define_the_required_oidc_process_policy() -> None:
    required = {
        "oidc_login_origin",
        "oidc_login_lifetime_seconds",
        "oidc_session_lifetime_seconds",
        "oidc_callback_rejection",
        "oidc_callback_unavailable",
        "oidc_connect_timeout_seconds",
        "oidc_read_timeout_seconds",
        "oidc_total_timeout_seconds",
        "oidc_token_response_max_bytes",
        "oidc_jwks_response_max_bytes",
        "oidc_jwks_cache_ttl_seconds",
    }
    assert required <= PlatformSettings.model_fields.keys()


def test_runtime_environment_contract_lists_the_complete_oidc_group() -> None:
    example = (
        Path(__file__).resolve().parents[1]
        / "operations"
        / "compose"
        / "runtime.env.example"
    ).read_text(encoding="utf-8")
    for field in PlatformSettings.model_fields:
        if field.startswith("oidc_"):
            assert f"LIQUENT_{field.upper()}=" in example


def test_persistent_runtime_lookups_expose_no_management_shortcut() -> None:
    forbidden = {
        "create",
        "set",
        "replace",
        "activate",
        "deactivate",
        "delete",
        "grant",
        "revoke",
        "add_membership",
        "set_permissions",
    }
    assert forbidden.isdisjoint(vars(DatabaseActiveOidcClientConfiguration))
    assert forbidden.isdisjoint(vars(DatabaseWorkspaceMemberships))


def test_oidc_trust_operator_is_not_imported_by_the_runtime_process() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")

    assert "operators.oidc_trust" not in source
    assert "oidc_trust_changes" not in source
    assert "oidc_trust_bootstrap" not in source


def test_http_factory_exposes_no_identity_or_authority_management_route() -> None:
    app = create_app(PlatformSettings(_secrets_dir=None))
    paths = {route.path for route in app.routes}

    forbidden_fragments = {
        "bootstrap",
        "membership",
        "permission",
        "authority",
        "trust",
        "onboarding",
    }
    assert all(
        fragment not in path
        for path in paths
        for fragment in forbidden_fragments
    )


def test_packaged_operator_inventory_has_bootstrap_and_membership_tools() -> None:
    pyproject = (
        Path(__file__).resolve().parents[1] / "pyproject.toml"
    ).read_text(encoding="utf-8")

    assert "liquent-oidc-trust" in pyproject
    assert "liquent-initial-bootstrap" in pyproject
    assert "liquent-membership-management" in pyproject
