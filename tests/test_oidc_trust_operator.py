import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.oidc_trust import OidcTrustChangeKind
from liquent_platform.operators.oidc_trust import (
    OidcTrustOperatorInputRejected,
    load_operator_request,
    main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _configuration() -> dict[str, Any]:
    return {
        "issuer": "https://idp.example",
        "authorization_endpoint": "https://idp.example/authorize",
        "client_id": "operator-client",
        "redirect_uri": "https://app.example/callback",
        "scopes": ["openid", "profile"],
        "token_endpoint": "https://idp.example/token",
        "jwks_uri": "https://idp.example/jwks",
        "allowed_signing_algorithms": ["RS256"],
        "clock_skew_seconds": 30,
    }


def _request(**overrides: Any) -> dict[str, Any]:
    request = {
        "actor_user_id": "operator-user",
        "change_id": "stable-change-203",
        "kind": "activate",
        "expected_revision": None,
        "configuration": _configuration(),
    }
    request.update(overrides)
    return request


def _private_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'operator.db'}"
    upgrade_to_head(url)
    database = build_engine(url)
    with database.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users (user_id,status)"
            " VALUES (:user,'active')"
        ), {"user": b"operator-user"})
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities (user_id,status)"
            " VALUES (:user,'active')"
        ), {"user": b"operator-user"})
    try:
        yield database
    finally:
        database.dispose()


def test_private_exact_request_is_loaded_without_value_normalization(
    tmp_path: Path,
) -> None:
    path = _private_file(tmp_path / "request.json", json.dumps(_request()))

    request = load_operator_request(path)

    assert request.actor_user_id == "operator-user"
    assert request.change_id.value == "stable-change-203"
    assert request.kind is OidcTrustChangeKind.ACTIVATE
    assert request.configuration is not None
    assert request.configuration.client_id == "operator-client"
    assert "stable-change-203" not in repr(request)
    assert "operator-client" not in repr(request)


@pytest.mark.parametrize(
    "payload",
    [
        {**_request(), "unexpected": True},
        _request(change_id=""),
        _request(kind="unknown"),
        _request(expected_revision="revision", kind="activate"),
        _request(configuration=None, kind="rotate", expected_revision="revision"),
        _request(configuration={**_configuration(), "extra": "value"}),
    ],
)
def test_non_exact_request_is_rejected_detail_free(
    tmp_path: Path, payload: dict[str, Any]
) -> None:
    path = _private_file(tmp_path / "request.json", json.dumps(payload))

    with pytest.raises(OidcTrustOperatorInputRejected) as raised:
        load_operator_request(path)

    assert raised.value.args == ("oidc_trust_operator_input_rejected",)
    assert raised.value.__cause__ is None


def test_request_file_must_not_be_group_or_world_accessible(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(_request()), encoding="utf-8")
    path.chmod(0o640)

    with pytest.raises(OidcTrustOperatorInputRejected):
        load_operator_request(path)


def test_request_file_must_not_be_a_symbolic_link(tmp_path: Path) -> None:
    target = _private_file(tmp_path / "target.json", json.dumps(_request()))
    link = tmp_path / "request.json"
    link.symlink_to(target)

    with pytest.raises(OidcTrustOperatorInputRejected):
        load_operator_request(link)


def test_new_change_id_emits_one_fresh_opaque_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["new-change-id"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.strip()) >= 43
    assert "{" not in output.out


def test_operator_is_packaged_as_a_separate_console_entry_point() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    assert (
        'liquent-oidc-trust = "liquent_platform.operators.oidc_trust:main"'
        in pyproject
    )


def test_apply_and_exact_retry_use_the_preserved_change_id(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = _private_file(tmp_path / "request.json", json.dumps(_request()))
    database_url = _private_file(tmp_path / "database-url", str(engine.url))

    assert main([
        "apply", "--database-url-file", str(database_url), "--request", str(request)
    ]) == 0
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
        ))
    assert main([
        "apply", "--database-url-file", str(database_url), "--request", str(request)
    ]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        '{"outcome":"applied"}', '{"outcome":"applied"}'
    ]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM authorized_oidc_trust_changes"
        )) == 1


def test_neutral_authority_rejection_has_no_configuration_detail(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
        ))
    request = _private_file(tmp_path / "request.json", json.dumps(_request()))
    database_url = _private_file(tmp_path / "database-url", str(engine.url))

    exit_code = main([
        "apply", "--database-url-file", str(database_url), "--request", str(request)
    ])

    output = capsys.readouterr()
    assert exit_code == 5
    assert output.out == '{"outcome":"rejected"}\n'
    assert "operator-client" not in output.out + output.err


def test_malformed_input_exits_without_echoing_its_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = _private_file(
        tmp_path / "request.json", '{"client_secret":"DO-NOT-ECHO"}'
    )
    database_url = _private_file(tmp_path / "database-url", "not-used")

    with pytest.raises(SystemExit) as raised:
        main([
            "apply", "--database-url-file", str(database_url),
            "--request", str(request),
        ])

    output = capsys.readouterr()
    assert raised.value.code == 2
    assert output.out == ""
    assert output.err == '{"error":"oidc_trust_operator_input_rejected"}\n'
    assert "DO-NOT-ECHO" not in output.err
