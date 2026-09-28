import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.operators.initial_bootstrap import bootstrap_identity
from liquent_platform.operators.oidc_admission_login import (
    OidcAdmissionLoginOperatorRequest,
    apply_operator_request,
    load_operator_request,
)
from liquent_platform.persistence.oidc_login_transactions import (
    DatabaseOidcLoginTransactions,
)

NOW = datetime(2026, 9, 8, 17, tzinfo=UTC)


def _request(engine: Engine) -> OidcAdmissionLoginOperatorRequest:
    bootstrap = bootstrap_identity(engine, SecureIdentityAuthorityMaterialGenerator())
    assert bootstrap is not None
    return OidcAdmissionLoginOperatorRequest(
        bootstrap.result.user_id,
        SecureIdentityAuthorityMaterialGenerator().new_onboarding_decision_id(),
        bootstrap.result.user_id,
        bootstrap.result.workspace_id,
    )


def _start(engine: Engine) -> None:
    pending = PendingOidcLoginTransaction(
        expected_issuer="https://issuer.example",
        expected_nonce="nonce",
        code_verifier="verifier",
        redirect_uri="https://app.example/callback",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    assert DatabaseOidcLoginTransactions(engine, now=lambda: NOW).add_transaction(
        OidcLoginState("hidden-state"), pending
    )


@pytest.mark.postgres_integration
def test_operator_provisions_once_then_binds_after_login_start(
    postgres_engine: Engine,
) -> None:
    request = _request(postgres_engine)
    material = SecureIdentityAuthorityMaterialGenerator()

    assert apply_operator_request(
        postgres_engine, request, material=material, now=NOW
    ) is False
    _start(postgres_engine)
    assert apply_operator_request(
        postgres_engine, request, material=material, now=NOW
    ) is True

    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM authorized_onboarding_decisions"
        )) == 1
        assert connection.scalar(text("SELECT count(*) FROM identity_admissions")) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM oidc_login_transactions"
            " WHERE admission_id IS NOT NULL"
        )) == 1


def test_request_file_is_private_exact_and_repr_free(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps({
        "actor_user_id": "actor",
        "decision_id": "decision",
        "target_user_id": "target",
        "target_workspace_id": "workspace",
    }), encoding="utf-8")
    path.chmod(0o600)

    request = load_operator_request(path)
    assert "actor" not in repr(request)
    assert "decision" not in repr(request)
    assert "target" not in repr(request)
    assert "workspace" not in repr(request)


def test_entry_point_is_packaged() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert (
        'liquent-oidc-admission-login = '
        '"liquent_platform.operators.oidc_admission_login:main"'
    ) in pyproject
