import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.operators.membership_authority import (
    MembershipAuthorityOperatorInputRejected,
    load_anchor_request as load_membership_anchor,
    load_lifecycle_request as load_membership_lifecycle,
    main as membership_main,
)
from liquent_platform.operators.oidc_trust_authority import (
    OidcTrustAuthorityOperatorInputRejected,
    load_anchor_request as load_oidc_anchor,
    load_lifecycle_request as load_oidc_lifecycle,
    main as oidc_main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _oidc_anchor(**overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": "operator-actor",
        "change_id": "operator-oidc-anchor",
    }
    value.update(overrides)
    return value


def _oidc_change(revision: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": "operator-actor",
        "change_id": "operator-oidc-change",
        "target_user_id": "operator-target",
        "intent": "grant",
        "expected_revision": revision,
    }
    value.update(overrides)
    return value


def _membership_anchor(**overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": "operator-actor",
        "change_id": "operator-membership-anchor",
        "workspace_id": "operator-workspace",
    }
    value.update(overrides)
    return value


def _membership_change(revision: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": "operator-actor",
        "change_id": "operator-membership-change",
        "target_user_id": "operator-target",
        "workspace_id": "operator-workspace",
        "intent": "grant",
        "expected_revision": revision,
    }
    value.update(overrides)
    return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'operator.db'}"
    upgrade_to_head(url)
    database = build_engine(url)
    with database.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:actor,'active'),(:target,'active')"
        ), {"actor": b"operator-actor", "target": b"operator-target"})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": b"operator-workspace"})
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:actor,'active')"
        ), {"actor": b"operator-actor"})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": b"operator-actor", "workspace": b"operator-workspace"})
    try:
        yield database
    finally:
        database.dispose()


def test_exact_private_requests_parse_without_exposing_identifiers(
    tmp_path: Path,
) -> None:
    oidc_anchor = load_oidc_anchor(_private(
        tmp_path / "oidc-anchor.json", json.dumps(_oidc_anchor())
    ))
    oidc_change = load_oidc_lifecycle(_private(
        tmp_path / "oidc-change.json", json.dumps(_oidc_change("revision"))
    ))
    membership_anchor = load_membership_anchor(_private(
        tmp_path / "membership-anchor.json", json.dumps(_membership_anchor())
    ))
    membership_change = load_membership_lifecycle(_private(
        tmp_path / "membership-change.json",
        json.dumps(_membership_change("revision")),
    ))

    assert oidc_change.intent.value == "grant"
    assert membership_change.intent.value == "grant"
    assert "operator-actor" not in repr(
        oidc_anchor
    ) + repr(oidc_change) + repr(membership_anchor) + repr(membership_change)


@pytest.mark.parametrize(
    ("loader", "payload", "failure"),
    [
        (load_oidc_anchor, {**_oidc_anchor(), "allow": True},
         OidcTrustAuthorityOperatorInputRejected),
        (load_oidc_lifecycle, _oidc_change("revision", intent="anchor"),
         OidcTrustAuthorityOperatorInputRejected),
        (load_oidc_lifecycle, _oidc_change(""),
         OidcTrustAuthorityOperatorInputRejected),
        (load_membership_anchor, {**_membership_anchor(), "role": "admin"},
         MembershipAuthorityOperatorInputRejected),
        (load_membership_lifecycle,
         _membership_change("revision", intent="recover"),
         MembershipAuthorityOperatorInputRejected),
        (load_membership_lifecycle, _membership_change(""),
         MembershipAuthorityOperatorInputRejected),
    ],
)
def test_non_exact_or_non_regular_requests_are_rejected_detail_free(
    tmp_path: Path, loader, payload: dict[str, Any], failure
) -> None:
    path = _private(tmp_path / "bad.json", json.dumps(payload))

    with pytest.raises(failure) as raised:
        loader(path)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("main", [oidc_main, membership_main])
def test_new_change_id_emits_one_opaque_value(main, capsys) -> None:
    assert main(["new-change-id"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.strip()) >= 43
    assert "{" not in output.out


def test_oidc_cli_anchors_applies_and_exactly_retries(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    anchor_request = _private(
        tmp_path / "anchor.json", json.dumps(_oidc_anchor())
    )
    anchor_result = tmp_path / "anchor-result.json"
    assert oidc_main([
        "anchor", "--database-url-file", str(database), "--request",
        str(anchor_request), "--result-file", str(anchor_result),
    ]) == 0
    anchor = json.loads(anchor_result.read_text(encoding="utf-8"))
    change_request = _private(
        tmp_path / "change.json",
        json.dumps(_oidc_change(anchor["revision_id"])),
    )
    first = tmp_path / "first.json"
    assert oidc_main([
        "apply", "--database-url-file", str(database), "--request",
        str(change_request), "--result-file", str(first),
    ]) == 0
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
            " WHERE user_id=:actor"
        ), {"actor": b"operator-actor"})
    repeated = tmp_path / "repeated.json"
    assert oidc_main([
        "apply", "--database-url-file", str(database), "--request",
        str(change_request), "--result-file", str(repeated),
    ]) == 0

    assert first.read_text(encoding="utf-8") == repeated.read_text(encoding="utf-8")
    assert first.stat().st_mode & 0o777 == 0o600
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        '{"outcome":"anchored"}',
        '{"outcome":"applied"}',
        '{"outcome":"applied"}',
    ]


def test_membership_cli_anchors_applies_and_preserves_scope(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    anchor_request = _private(
        tmp_path / "anchor.json", json.dumps(_membership_anchor())
    )
    anchor_result = tmp_path / "anchor-result.json"
    assert membership_main([
        "anchor", "--database-url-file", str(database), "--request",
        str(anchor_request), "--result-file", str(anchor_result),
    ]) == 0
    anchor = json.loads(anchor_result.read_text(encoding="utf-8"))
    change_request = _private(
        tmp_path / "change.json",
        json.dumps(_membership_change(anchor["revision_id"])),
    )
    change_result = tmp_path / "change-result.json"
    assert membership_main([
        "apply", "--database-url-file", str(database), "--request",
        str(change_request), "--result-file", str(change_result),
    ]) == 0

    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,workspace_id,status"
            " FROM workspace_membership_management_authorities"
            " WHERE user_id=:target"
        ), {"target": b"operator-target"}).one() == (
            b"operator-target", b"operator-workspace", "active"
        )
    assert set(json.loads(
        change_result.read_text(encoding="utf-8")
    )) == {"change_id", "revision_id"}
    assert capsys.readouterr().out.splitlines() == [
        '{"outcome":"anchored"}', '{"outcome":"applied"}'
    ]


@pytest.mark.parametrize("main", [oidc_main, membership_main])
def test_operator_does_not_migrate_empty_database(
    main, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(
        tmp_path / "database-url", f"sqlite:///{tmp_path / 'empty.db'}"
    )
    request_value = _oidc_anchor() if main is oidc_main else _membership_anchor()
    request = _private(tmp_path / "request.json", json.dumps(request_value))

    with pytest.raises(SystemExit) as raised:
        main([
            "anchor", "--database-url-file", str(database), "--request",
            str(request), "--result-file", str(tmp_path / "result.json"),
        ])
    assert raised.value.code == 4
    assert "operator_unavailable" in capsys.readouterr().err


def test_existing_result_is_never_overwritten(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(tmp_path / "request.json", json.dumps(_oidc_anchor()))
    result = _private(tmp_path / "result.json", "KEEP")

    with pytest.raises(SystemExit) as raised:
        oidc_main([
            "anchor", "--database-url-file", str(database), "--request",
            str(request), "--result-file", str(result),
        ])
    assert raised.value.code == 4
    assert result.read_text(encoding="utf-8") == "KEEP"
    assert "operator-actor" not in capsys.readouterr().err


def test_console_entry_points_are_separate() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert (
        'liquent-oidc-trust-authority = '
        '"liquent_platform.operators.oidc_trust_authority:main"'
    ) in pyproject
    assert (
        'liquent-membership-authority = '
        '"liquent_platform.operators.membership_authority:main"'
    ) in pyproject
