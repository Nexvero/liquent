import json
from pathlib import Path

import pytest
from sqlalchemy import text

from liquent_platform.operators import release_publication_executor as operator
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _private(path: Path, value: str) -> Path:
    path.write_text(value)
    path.chmod(0o600)
    return path


def _request(tmp_path: Path, value=None) -> Path:
    payload = {"registration_id": "registration-284"} if value is None else value
    return _private(
        tmp_path / "request.json",
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
    )


def test_operator_registers_and_exactly_recovers_executor(tmp_path, capsys):
    database_path = tmp_path / "executor.db"
    engine = build_engine(f"sqlite:///{database_path}")
    upgrade_to_head(str(engine.url))
    engine.dispose()
    database = _private(
        tmp_path / "database-url", f"sqlite:///{database_path}\n"
    )
    arguments = [
        "register", "--database-url-file", str(database),
        "--request", str(_request(tmp_path)),
    ]

    assert operator.main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    assert set(first) == {"executor_id", "outcome", "registration_id"}
    assert first["outcome"] == "registered"
    assert operator.main(arguments) == 0
    assert json.loads(capsys.readouterr().out) == first

    verify = build_engine(f"sqlite:///{database_path}")
    with verify.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_executors),"
            " (SELECT count(*) FROM release_publication_executor_registrations),"
            " (SELECT count(*) FROM release_publication_handoffs),"
            " (SELECT count(*) FROM release_publication_executions)"
        )).one() == (1, 1, 0, 0)
    verify.dispose()


@pytest.mark.parametrize("payload", [
    {"registration_id": "registration", "executor_id": "caller"},
    {"registration_id": "registration", "allow": True},
    {"registration_id": "registration", "role": "publisher"},
])
def test_request_rejects_open_executor_or_authority_fields(tmp_path, payload):
    with pytest.raises(operator.ReleasePublicationExecutorOperatorInputRejected):
        operator.load_request(_request(tmp_path, payload))


def test_main_maps_input_and_unavailability_detail_free(tmp_path, monkeypatch, capsys):
    arguments = [
        "register", "--database-url-file", str(tmp_path / "database"),
        "--request", str(tmp_path / "request"),
    ]
    for error, status, code in (
        (operator.ReleasePublicationExecutorOperatorInputRejected(), 2,
         "release_publication_executor_operator_input_rejected"),
        (operator.ReleasePublicationExecutorOperatorUnavailable(), 4,
         "release_publication_executor_operator_unavailable"),
    ):
        monkeypatch.setattr(
            operator, "run_operator",
            lambda error=error, **_: (_ for _ in ()).throw(error),
        )
        with pytest.raises(SystemExit) as caught:
            operator.main(arguments)
        assert caught.value.code == status
        assert json.loads(capsys.readouterr().err) == {"error": code}
