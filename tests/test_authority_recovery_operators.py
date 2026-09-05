import json
from pathlib import Path
from typing import Any

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
    MembershipAuthorityRecoveryOperatorInputRejected,
    load_recovery_request as load_membership_request,
    main as membership_main,
)
from liquent_platform.operators.oidc_trust_authority_recovery import (
    OidcTrustAuthorityRecoveryOperatorInputRejected,
    load_recovery_request as load_oidc_request,
    main as oidc_main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)

TARGET = UserId("recovery-operator-target")
FORMER = UserId("recovery-operator-former")
WORKSPACE = WorkspaceId("recovery-operator-workspace")
OIDC_EXPECTED = "recovery-operator-oidc-expected"
MEMBERSHIP_EXPECTED = "recovery-operator-membership-expected"


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _oidc_request(**overrides: Any) -> dict[str, Any]:
    value = {
        "recovery_id": "recovery-operator-oidc-id",
        "target_user_id": str(TARGET),
        "expected_revision": OIDC_EXPECTED,
    }
    value.update(overrides)
    return value


def _membership_request(**overrides: Any) -> dict[str, Any]:
    value = {
        "recovery_id": "recovery-operator-membership-id",
        "target_user_id": str(TARGET),
        "workspace_id": str(WORKSPACE),
        "expected_revision": MEMBERSHIP_EXPECTED,
    }
    value.update(overrides)
    return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'recovery-operator.db'}"
    upgrade_to_head(url)
    database = build_engine(url)
    with database.begin() as connection:
        for user in (TARGET, FORMER):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": WORKSPACE.encode()},
        )
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:target,'inactive'),(:former,'active')"
        ), {"target": TARGET.encode(), "former": FORMER.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:target,:workspace,'inactive'),(:former,:workspace,'active')"
        ), {
            "target": TARGET.encode(), "former": FORMER.encode(),
            "workspace": WORKSPACE.encode(),
        })
    assert DatabaseOidcTrustAuthoritySetAnchor(
        database,
        generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
            OIDC_EXPECTED
        ),
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("recovery-operator-oidc-anchor"),
        SessionPrincipal(FORMER),
    )
    assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
        database,
        generate_revision_id=lambda: WorkspaceMembershipAuthoritySetRevisionId(
            MEMBERSHIP_EXPECTED
        ),
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "recovery-operator-membership-anchor"
        ),
        SessionPrincipal(FORMER), WORKSPACE,
    )
    with database.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:former"),
            {"former": FORMER.encode()},
        )
    try:
        yield database
    finally:
        database.dispose()


def test_exact_private_requests_are_repr_free(tmp_path: Path) -> None:
    oidc = load_oidc_request(_private(
        tmp_path / "oidc.json", json.dumps(_oidc_request())
    ))
    membership = load_membership_request(_private(
        tmp_path / "membership.json", json.dumps(_membership_request())
    ))

    assert oidc.expected_revision.value == OIDC_EXPECTED
    assert membership.workspace_id == WORKSPACE
    assert str(TARGET) not in repr(oidc) + repr(membership)


@pytest.mark.parametrize(
    ("loader", "payload", "failure"),
    [
        (load_oidc_request, {**_oidc_request(), "actor_user_id": "actor"},
         OidcTrustAuthorityRecoveryOperatorInputRejected),
        (load_oidc_request, {**_oidc_request(), "allow": True},
         OidcTrustAuthorityRecoveryOperatorInputRejected),
        (load_oidc_request, _oidc_request(recovery_id=""),
         OidcTrustAuthorityRecoveryOperatorInputRejected),
        (load_membership_request,
         {**_membership_request(), "intent": "reactivate"},
         MembershipAuthorityRecoveryOperatorInputRejected),
        (load_membership_request, {**_membership_request(), "role": "admin"},
         MembershipAuthorityRecoveryOperatorInputRejected),
        (load_membership_request, _membership_request(expected_revision=""),
         MembershipAuthorityRecoveryOperatorInputRejected),
    ],
)
def test_extra_authority_inputs_and_invalid_shapes_are_rejected(
    tmp_path: Path, loader, payload: dict[str, Any], failure
) -> None:
    path = _private(tmp_path / "bad.json", json.dumps(payload))
    with pytest.raises(failure) as raised:
        loader(path)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("main", [oidc_main, membership_main])
def test_new_recovery_id_emits_one_opaque_value(main, capsys) -> None:
    assert main(["new-recovery-id"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.strip()) >= 43
    assert "{" not in output.out


def test_oidc_recovery_and_exact_retry_write_protected_results(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(tmp_path / "request.json", json.dumps(_oidc_request()))
    first = tmp_path / "first.json"
    assert oidc_main([
        "recover", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(first),
    ]) == 0
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:target"),
            {"target": TARGET.encode()},
        )
    repeated = tmp_path / "repeated.json"
    assert oidc_main([
        "recover", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(repeated),
    ]) == 0

    assert first.read_text(encoding="utf-8") == repeated.read_text(encoding="utf-8")
    assert first.stat().st_mode & 0o777 == 0o600
    assert set(json.loads(first.read_text(encoding="utf-8"))) == {
        "recovery_id", "revision_id"
    }
    assert capsys.readouterr().out.splitlines() == [
        '{"outcome":"recovered"}', '{"outcome":"recovered"}'
    ]


def test_membership_recovery_is_workspace_scoped(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(
        tmp_path / "request.json", json.dumps(_membership_request())
    )
    result = tmp_path / "result.json"
    assert membership_main([
        "recover", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(result),
    ]) == 0

    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM workspace_membership_management_authorities"
            " WHERE user_id=:target AND workspace_id=:workspace"
        ), {"target": TARGET.encode(), "workspace": WORKSPACE.encode()}) == "active"
    assert capsys.readouterr().out == '{"outcome":"recovered"}\n'


@pytest.mark.parametrize("main", [oidc_main, membership_main])
def test_operator_does_not_migrate_empty_database(
    main, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(
        tmp_path / "database-url", f"sqlite:///{tmp_path / 'empty.db'}"
    )
    payload = _oidc_request() if main is oidc_main else _membership_request()
    request = _private(tmp_path / "request.json", json.dumps(payload))
    with pytest.raises(SystemExit) as raised:
        main([
            "recover", "--database-url-file", str(database), "--request",
            str(request), "--result-file", str(tmp_path / "result.json"),
        ])
    assert raised.value.code == 4
    assert "operator_unavailable" in capsys.readouterr().err


def test_existing_result_is_never_overwritten(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(tmp_path / "request.json", json.dumps(_oidc_request()))
    result = _private(tmp_path / "result.json", "KEEP")
    with pytest.raises(SystemExit) as raised:
        oidc_main([
            "recover", "--database-url-file", str(database), "--request",
            str(request), "--result-file", str(result),
        ])
    assert raised.value.code == 4
    assert result.read_text(encoding="utf-8") == "KEEP"
    assert str(TARGET) not in capsys.readouterr().err


def test_console_entry_points_are_separate() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert (
        'liquent-oidc-trust-authority-recovery = '
        '"liquent_platform.operators.oidc_trust_authority_recovery:main"'
    ) in pyproject
    assert (
        'liquent-membership-authority-recovery = '
        '"liquent_platform.operators.membership_authority_recovery:main"'
    ) in pyproject
