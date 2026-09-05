import json
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.operators import release_publication_bootstrap as operator
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _private(path: Path, value: str) -> Path:
    path.write_text(value)
    path.chmod(0o600)
    return path


def _json(path: Path, value: dict[str, object]) -> Path:
    return _private(
        path, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    )


def _request(tmp_path: Path, **changes) -> Path:
    value = {
        "bootstrap_id": "publication-bootstrap-lq281",
        "package_name": "liquent",
        "provider_kind": "package-index",
        "target_name": "stable",
    }
    value.update(changes)
    return _json(tmp_path / "request.json", value)


def test_operator_bootstraps_and_exactly_recovers_protected_ids(
    tmp_path: Path, capsys
):
    database_path = tmp_path / "publication.db"
    engine = build_engine(f"sqlite:///{database_path}")
    upgrade_to_head(str(engine.url))
    engine.dispose()
    database = _private(
        tmp_path / "database-url", f"sqlite:///{database_path}\n"
    )
    request = _request(tmp_path)
    arguments = [
        "--database-url-file", str(database), "--request", str(request),
    ]
    assert operator.main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    assert set(first) == {
        "bootstrap_id", "channel_id", "channel_revision_id", "outcome",
        "publisher_authority_id",
    }
    assert first["outcome"] == "bootstrapped"
    assert operator.main(arguments) == 0
    assert json.loads(capsys.readouterr().out) == first
    verify = build_engine(f"sqlite:///{database_path}")
    try:
        with verify.connect() as connection:
            assert connection.execute(text(
                "SELECT revision.package_name,revision.provider_kind,"
                " revision.target_name,revision.status,publisher.status"
                " FROM release_publication_current_channels current"
                " JOIN release_publication_channel_revisions revision"
                " ON revision.channel_id=current.channel_id"
                " AND revision.revision_id=current.revision_id"
                " JOIN release_publication_revision_publishers publisher"
                " ON publisher.channel_id=revision.channel_id"
                " AND publisher.revision_id=revision.revision_id"
            )).one() == (
                "liquent", "package-index", "stable", "active", "active"
            )
            assert connection.execute(text(
                "SELECT (SELECT count(*) FROM release_publication_handoffs),"
                " (SELECT count(*) FROM release_publication_executors),"
                " (SELECT count(*) FROM release_publication_executions)"
            )).one() == (0, 0, 0)
    finally:
        verify.dispose()


@pytest.mark.parametrize(
    "changes",
    [
        {"allow": True},
        {"publisher_authority_id": "caller"},
        {"package_name": "other"},
        {"provider_kind": "other-provider"},
        {"target_name": "../unstable"},
    ],
)
def test_request_rejects_open_authority_or_unsupported_channel(
    tmp_path: Path, changes
):
    with pytest.raises(operator.ReleasePublicationBootstrapOperatorInputRejected):
        operator.load_request(_request(tmp_path, **changes))


def test_main_separates_neutral_conflict_input_and_unavailable(
    tmp_path: Path, monkeypatch, capsys
):
    arguments = [
        "--database-url-file", str(tmp_path / "database"),
        "--request", str(tmp_path / "request"),
    ]
    monkeypatch.setattr(operator, "run_operator", lambda **_: None)
    assert operator.main(arguments) == 5
    assert capsys.readouterr().out == '{"outcome":"not_bootstrapped"}\n'
    monkeypatch.setattr(
        operator,
        "run_operator",
        lambda **_: (_ for _ in ()).throw(
            operator.ReleasePublicationBootstrapOperatorInputRejected()
        ),
    )
    with pytest.raises(SystemExit) as rejected:
        operator.main(arguments)
    assert rejected.value.code == 2
    assert capsys.readouterr().err == (
        '{"error":"release_publication_bootstrap_operator_input_rejected"}\n'
    )
